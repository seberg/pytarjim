#!/usr/bin/env python
#-*- coding:utf-8 -*-

__author__ = 'Sebastian Berg'
__license__ = 'LGPL v3'

import sys; sys.argv[0] = 'PyTarjim'
import os
import gtk, gobject
import pango

import tecpy

translits = [('Vocalize (No Alif)', 'map/mappings/arabtex-fdf2noalif-voc.map'.replace('/', os.path.sep)),
    ('Fullvocalize (No Alif)', 'map/mappings/arabtex-fdf2noalif-fullvoc.map'.replace('/', os.path.sep)),
    ('No vocalization (No Alif)', 'map/mappings/arabtex-fdf2noalif-novoc.map'.replace('/', os.path.sep)),
    ('Vocalize (Alif)', 'map/mappings/arabtex-fdf2alif-voc.map'.replace('/', os.path.sep)),
    ('Fullvocalize (Alif)', 'map/mappings/arabtex-fdf2alif-fullvoc.map'.replace('/', os.path.sep)),
    ('No vocalization (Alif)', 'map/mappings/arabtex-fdf2alif-novoc.map'.replace('/', os.path.sep)),
    ('DMG Transliteration', 'map/mappings/arabtex-trans-dmg.map'.replace('/', os.path.sep)),
    ('Transliteration', 'map/mappings/arabtex-trans-loc.map'.replace('/', os.path.sep))]

translit_dict = dict(translits)
config_file = 'pyjarjim_config.txt'

class Transliterator:
    def on_window_destroy(self, widget, data=None):
        pos = self.last_position
        size = self.last_size
        f = file(config_file, 'w')
        f.write('%i %i %i %i\n' % (pos[0], pos[1], size[0], size[1]))
        f.write(self.font_button.get_font_name())
        f.write('\n%s' % self.translitpicker.get_active())
        f.close()
        gtk.main_quit()
    

    def __init__(self):
        # use GtkBuilder to build our interface from the XML file 
        builder = gtk.Builder()
        builder.add_from_file("window.glade") 
    
        self.changed = False
        self.window = builder.get_object("window")
        
        self.text_trans = builder.get_object("trans")
        self.text_arab = builder.get_object("arabic")
        
        self.window.set_keep_above(True)
        self.trans_buffer = self.text_trans.get_buffer()
        self.arab_buffer = self.text_arab.get_buffer() 
        
        # connect signals
        builder.connect_signals(self)
        self.trans_buffer.connect('changed', self.idle_edited)
        
        self.font_button = builder.get_object('arabfontbutton')
        
        self.translitpicker = builder.get_object("translitpicker")
        self.translit_list_store = gtk.ListStore(gobject.TYPE_STRING)
        for n, _ in translits:
            self.translit_list_store.append([n])
        self.translitpicker.set_model(self.translit_list_store)
        cell = gtk.CellRendererText()
        self.translitpicker.pack_start(cell, True)
        self.translitpicker.add_attribute(cell, "text", 0)
        self.translitpicker.set_active(3)
        
        self.clipboard = gtk.Clipboard()
        
        try:
            f = file(config_file)
            l = f.read().split('\n')
            p = l[0].split()
            p = [int(_) for _ in p]
            self.window.move(*p[:2])
            self.window.resize(*p[2:4])
            
            self.font_button.set_font_name(l[1])
            self.translitpicker.set_active(int(l[2])) 
        except IOError:
            pass
        except:
            print 'Invalid Config file!'

        self.text_arab.modify_font(pango.FontDescription(self.font_button.get_font_name()))

        self.icon = gtk.StatusIcon()
        self.icon.set_from_file('icon.svg')
        self.icon.connect("activate", self.toggle_visibility)
        
        # just to make sure its not bogus
        self.last_position = self.window.get_position()
        self.last_size = self.window.get_size()
        
        self.last_position = self.window.get_position()

    
    def right_click_event(self, icon, button, time):
        self.menu = gtk.Menu()

        quit = gtk.MenuItem()
        quit.set_label("Quit")

        quit.connect("activate", self.close_from_tray)

        self.menu.append(quit)
        self.menu.show_all()
    
    
    def toggle_visibility(self, *args, **kwargs):
        visible = self.window.get_property("visible")
        
        if visible:
            self.last_position = self.window.get_position()
            self.last_size = self.window.get_size()
            self.window.hide()
        else:
            self.window.show()
            self.window.move(self.last_position[0], self.last_position[1])
        
    
    def font_changed(self, font_button):
        self.text_arab.modify_font(pango.FontDescription(font_button.get_font_name()))
    
    
    def edited(self, button=None):
        if not self.changed:
            return
        
        buf = self.trans_buffer
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        
        arabic = self.transliterate(text)
        
        self.arab_buffer.set_text(arabic)
        self.changed = False
    
    
    def copy_arab(self, button):
        buf = self.arab_buffer
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        self.clipboard.set_text(text)

    
    def clear(self, button):
        self.trans_buffer.set_text(u'')
        self.arab_buffer.set_text(u'')
    
    
    def idle_edited(self, text):
        self.changed = True
        
        gobject.idle_add(self.edited)
    
    
    def set_transliteration(self, picker):
        """Set transliteration Mapping.
        """
        #print picker.get_active()
        #print translits[picker.get_active()][1]
        self.transliterate = tecpy.Mapping(translits[picker.get_active()][1])
        self.changed = True
        
        gobject.idle_add(self.edited)
    
    def main(self):
        self.window.show()
        gtk.main()

if __name__ == "__main__":
    transliterator = Transliterator()
    transliterator.main()
