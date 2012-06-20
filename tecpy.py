#!/usr/bin/env python
#-*- coding:utf-8 -*-

__author__ = 'Sebastian Berg'
__license__ = 'LGPL v3'

import re

class _Control(unicode):
    pass
class _Group(unicode):
    pass


class Mapping(object):
    """Class to read a very simple .map files and create a python mapping for it.
    map file means a teckit .map function for parsing into .tec files...
    
    NOTES:  o Only forward direction is supported...
            o reads only line wise...
            o This is extremely limited...
            o Uses python regexes, and thus is probably slow as hell compared
                to real TecKit.
    """
    
    def __init__(self, file):
        """Given a .map file or string to it.
        """
        self.line_regexes = {re.compile(r'LHSName\s*"(?P<name>.*)"') : self.set_name,
            re.compile(r'^RHSName\s*"(?P<name>.*)"$') : None,
            re.compile(r'^Define\s+(?P<var>[A-z]+)\s+(?P<chars>.*)$') : self.set_def,
            re.compile(r'^pass\(Unicode\)$') : self.new_pass,
            re.compile(r'^(?P<ls>[^<>]+)(<>|>)(?P<rs>[^<>]*)$') : self.add_sub,
            re.compile(r'^Class\s*(?P<class>\[[A-z]+\])\s*=\s*\((?P<group>.*)\)$') : self.add_group,
        }
        self.definitions = {}
        self.passes = []
        
        if type(file) is str:
            file = open(file, 'r')
        
        for line in file.readlines():
            line = line.split(';')[0].strip() # remove comments, and whitespaces.
            if line == '':
                continue
            
            for r, f in self.line_regexes.iteritems():
                match = r.match(line)
                if match:
                    if f is not None:
                        f(match)
                    break
            else:
                print 'Unmatched line:'
                print '   ', repr(line)
        
        
    def set_name(self, match):
        self.name = match.groupdict()['name']
    
    
    def get_unicode_string(self, string):
        """Returns list of characters groups and everything.
        """
        s = re.findall('([()#<> |?\^]|@?=?[^()#<>= |?]*)', string)
        s = [c.strip() for c in s if c.strip() != '']
        res = []
        for c in s:
            if c.startswith('U+'):
                c = c.split('..')
                if len(c) == 1:
                    res.append((unichr(int(c[0][2:], 16))))
                else:
                    # brutal, as regex really could handle this too...
                    for i in xrange(int(c[0][2:], 16), int(c[1][2:], 16)+1):
                        res.append((unichr(i)))
            else:
                try:
                    c = self.definitions[c]
                    res.extend(c)
                except KeyError:
                    # this must be some control character:
                    res.append(_Control(c))
        
        return res
    
    
    def set_def(self, match):
        d = match.groupdict()
        new_def = self.get_unicode_string(d['chars'])
        
        self.definitions[d['var']] = new_def
        
    
    def add_group(self, match):
        d = match.groupdict()
        new_def = self.get_unicode_string(d['group'])
        
        if any([isinstance(c, _Control) for c in new_def]):
            raise NotImplementedError('A definition should not include control characters.')
        if any([isinstance(c, _Group) for c in new_def]):
            raise NotImplementedError('A definition should not include grouped characters/classes.')
        
        self.definitions[d['class']] = [_Group(u''.join(new_def))]

    def make_regex(self, commlist):
        string = []
        negate = False
        
        for m in commlist:
            if isinstance(m, _Control):
                if m == '^':
                    negate = True
                elif m == '#':
                    string.append(u'(^|\s|$)')
                elif m.startswith('='):
                    # OK, ugly hack:
                    if string[-1] == '?':
                        del string[-1]
                        string[-1] = u'(?P<%s>%s?)' % (m[1:], string[-1])
                    else:
                        string[-1] = u'(?P<%s>%s)' % (m[1:], string[-1])
                else:
                    string.append(m)
            else:
                if negate:
                    string.append(u'(?!(%s)).' % u'|'.join([re.escape(_) for _ in m]))
                    negate = False
                else:
                    string.append(u'(%s)' % u'|'.join([re.escape(_) for _ in m]))
            
            if m == ')' and len(string) != 1: # Closing bracket, so search the previous bracket and join this part.
                for prev_i, prev in enumerate(string[::-1]):
                    if prev == '(':
                        string[-prev_i-1] = u''.join(string[-prev_i-1:])
                        del string[-prev_i:]
                        break
                else:
                    # Don't care about unmachted brackets here, they seem to be handled somewhere else ;)
                    pass
        
        string = u''.join(string)
        return string
        
    
    def add_sub(self, match):
        d = match.groupdict()
        
        new = self.get_unicode_string(d['rs'].strip())
        
        if len(new) == 1:
            # This is a special case of group assignment...
            old = self.get_unicode_string(d['ls'].strip())
            if len(old) == 1:  
                new = new[0]
                old = old[0]
                if len(new) == len(old):
                    for n, o in zip(new, old):
                        o = re.escape(o)
                        n, _o = n, re.compile(o)
                        def add(o, n):
                            self.passes[-1].append([lambda x: o.sub(n, x), o, n])
                        add(_o, n)
                    return
                elif len(new) != 1:
                    raise NotImplementedError('For list of characters, length must equal')
        
        _new = new

        new = []
        for m in _new:
            if m.startswith('@'):
                new.append(u'%%(%s)s' % m[1:])
            else:
                new.append(m)
        new = u''.join(new)
        
        ls = d['ls'].strip().split('/')
        
        # We build ourself a mean regex now...
        middle = self.make_regex(self.get_unicode_string(ls[0]))
        
        if len(ls) > 1:
            l, r = ls[1].split('_')
            l = l.strip()
            if l == '':
                before = u''
            else:
                before = u'(?P<__before_>%s)' % self.make_regex(self.get_unicode_string(l))
                new = u'%(__before_)s' + new
            r = r.strip()
            if r == '':
                after = u''
            else:
                after = u'(?P<__after_>%s)' % self.make_regex(self.get_unicode_string(r))
                new = new + u'%(__after_)s'
            
            regex = re.compile(before + middle + after)
            self.passes[-1].append([lambda x: regex.sub(lambda m: new % m.groupdict(), x), before + middle + after, new])
        else:
            regex = re.compile(middle)
            self.passes[-1].append([lambda x: regex.sub(lambda m: new % m.groupdict(), x), middle, new])
    
    
    def new_pass(self, match):
        """This is actually not supposed to be used like this it seems. But
        in any case, it does not matter much...
        """
        self.passes.append([])
        


    def __call__(self, string):
        string = unicode(string)
        for p in self.passes:
            for sub in p:
                string = sub[0](string)
                
        return string
