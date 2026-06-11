
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtWidgets import *

import traceback
import os

from mcedit_ui.uic.ui_sprite_editor import Ui_SpriteEditor

from mcedit_ui.clickable_graphics_scene import *
from mcedit_ui.custom_graphics_items import *

from mclib.sprite_loading import SpriteLoadingData
from mclib.sprite import Sprite
from mclib.docs import Docs

class SpriteEditorDialog(QDialog):
  def __init__(self, main_window):
    super().__init__(main_window)
    self.ui = Ui_SpriteEditor()
    self.ui.setupUi(self)
    
    self.game = main_window.game
    self.rom = self.game.rom
    self.renderer = main_window.renderer
    
    self.type = -1
    self.subtype = -1
    self.form = -1
    
    self.sprite_graphics_scene = ClickableGraphicsScene()
    self.ui.sprite_graphics_view.setScene(self.sprite_graphics_scene)
    
    self.btn_export = QPushButton("Export Sprite Frames")
    self.ui.buttonBox.addButton(self.btn_export, QDialogButtonBox.ActionRole)
    self.btn_export.clicked.connect(self.export_sprite_frames)
    self.btn_export.setEnabled(False)
    
    self.btn_export_all_forms = QPushButton("Export All Forms")
    self.ui.horizontalLayout_2.addWidget(self.btn_export_all_forms)
    self.btn_export_all_forms.clicked.connect(self.export_all_forms)
    self.btn_export_all_forms.setEnabled(False)
    
    self.ui.enemy_list.currentRowChanged.connect(self.enemy_changed)
    self.ui.object_list.currentRowChanged.connect(self.object_changed)
    self.ui.npc_list.currentRowChanged.connect(self.npc_changed)
    self.ui.player_list.currentRowChanged.connect(self.player_changed)
    self.ui.type_4s_list.currentRowChanged.connect(self.type_4_changed)
    self.ui.player_items_list.currentRowChanged.connect(self.player_item_changed)
    
    self.ui.form_index.activated.connect(self.form_changed)
    self.ui.anim_index.activated.connect(self.anim_changed)
    self.ui.frame_index.activated.connect(self.frame_changed)
    
    self.type_to_list_widget = {
      3: self.ui.enemy_list,
      6: self.ui.object_list,
      7: self.ui.npc_list,
      1: self.ui.player_list,
      4: self.ui.type_4s_list,
      8: self.ui.player_items_list,
    }
    self.type_and_row_index_to_subtype = {}
    for type, list_widget in self.type_to_list_widget.items():
      self.type_and_row_index_to_subtype[type] = []
      
      subtypes = Docs.get_all_subtypes_for_type("entity", type)
      for subtype in subtypes:
        self.type_and_row_index_to_subtype[type].append(subtype)
        
        form = -1 # TODO kinda hacky to do it this way
        text = "%02X-%02X  %s" % (
          type, subtype,
          Docs.get_name_for_entity("entity", type, subtype, form)
        )
        list_widget.addItem(text)
    
    self.show()
  
  def enemy_changed(self, row_index):
    type = 3
    subtype = self.type_and_row_index_to_subtype[type][row_index]
    form = 0
    self.sprite_changed(type, subtype, form)
  
  def object_changed(self, row_index):
    type = 6
    subtype = self.type_and_row_index_to_subtype[type][row_index]
    form = 0
    self.sprite_changed(type, subtype, form)
  
  def npc_changed(self, row_index):
    type = 7
    subtype = self.type_and_row_index_to_subtype[type][row_index]
    form = 0
    self.sprite_changed(type, subtype, form)
  
  def player_changed(self, row_index):
    type = 1
    subtype = self.type_and_row_index_to_subtype[type][row_index]
    form = 0
    self.sprite_changed(type, subtype, form)
  
  def type_4_changed(self, row_index):
    type = 4
    subtype = self.type_and_row_index_to_subtype[type][row_index]
    form = 0
    self.sprite_changed(type, subtype, form)
  
  def player_item_changed(self, row_index):
    type = 8
    subtype = self.type_and_row_index_to_subtype[type][row_index]
    form = 0
    self.sprite_changed(type, subtype, form)
  
  def form_changed(self, form):
    self.sprite_changed(self.type, self.subtype, form)
  
  def sprite_changed(self, type, subtype, form):
    #print(type, subtype, form)
    
    if self.type == type and self.subtype == subtype:
      only_form_changed = True
    else:
      only_form_changed = False
    
    self.type = type
    self.subtype = subtype
    self.form = form
    
    self.sprite_graphics_scene.clear()
    self.ui.anim_index.clear()
    self.ui.frame_index.clear()
    if not only_form_changed:
      self.ui.form_index.clear()
      forms = Docs.get_all_forms_for_subtype("entity", self.type, self.subtype)
      for other_form in forms:
        form_name = Docs.get_name_for_entity_form("entity", self.type, self.subtype, other_form)
        self.ui.form_index.addItem("%02X %s" % (other_form, form_name))
    
    self.loading_data = SpriteLoadingData(type, subtype, form, self.rom)
    if self.loading_data.has_no_sprite:
      self.sprite = None
      self.btn_export.setEnabled(False)
      self.btn_export_all_forms.setEnabled(False)
      return
    
    self.sprite = Sprite(self.loading_data.sprite_index, self.rom)
    self.btn_export.setEnabled(True)
    self.btn_export_all_forms.setEnabled(True)
    
    # TODO: how to determine number of anims and frames?
    num_frames = 0xFF
    num_anims = 0xFF
    
    for i in range(num_frames):
      self.ui.frame_index.addItem("%02X" % i)
    
    if self.sprite.animation_list_ptr == 0:
      self.frame_changed(0)
    else:
      for i in range(num_anims):
        self.ui.anim_index.addItem("%02X" % i)
      
      self.anim_changed(0)
  
  def anim_changed(self, anim_index):
    self.ui.anim_index.setCurrentIndex(anim_index)
    
    try:
      anim = self.sprite.get_animation(anim_index)
    except Exception as e:
      stack_trace = traceback.format_exc()
      error_message = "Error getting animation:\n" + str(e) + "\n\n" + stack_trace
      QMessageBox.warning(self,
        "Error getting animation",
        error_message
      )
    
    keyframe = anim.keyframes[0]
    # TODO: how to handle the keyframe's h and v flip?
    frame_index = keyframe.frame_index
    
    self.frame_changed(frame_index)
  
  def frame_changed(self, frame_index):
    self.ui.frame_index.setCurrentIndex(frame_index)
    
    self.sprite_graphics_scene.clear()
    
    try:
      offsets = (0, 0)
      extra_frame_indexes = []
      frame_image, x_off, y_off = self.renderer.render_entity_frame(self.loading_data, frame_index, offsets, extra_frame_indexes)
    except Exception as e:
      stack_trace = traceback.format_exc()
      error_message = "Error rendering frame:\n" + str(e) + "\n\n" + stack_trace
      QMessageBox.warning(self,
        "Error rendering frame",
        error_message
      )
    
    if frame_image == None:
      return
    
    item = GraphicsImageItem(frame_image, x_off, y_off, draw_border=False)
    item.setPos(x_off, y_off)
    self.sprite_graphics_scene.addItem(item)
  
  def export_sprite_frames(self):
    if self.sprite is None:
      return
      
    dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Export Frames")
    if not dir_path:
      return
      
    entity_name = Docs.get_name_for_entity("entity", self.type, self.subtype, self.form)
    clean_name = "".join(c for c in entity_name if c.isalnum() or c in (' ', '_', '-')).strip()
    folder_name = "%02X_%02X_%02X_%s" % (self.type, self.subtype, self.form, clean_name)
    export_dir = os.path.join(dir_path, folder_name)
    os.makedirs(export_dir, exist_ok=True)
    
    exported_count = 0
    for frame_index in range(256):
      try:
        frame_image, x_off, y_off = self.renderer.render_entity_frame(self.loading_data, frame_index, (0, 0), [])
        if frame_image is not None:
          file_path = os.path.join(export_dir, "frame_%02X.png" % frame_index)
          frame_image.save(file_path)
          exported_count += 1
      except Exception:
        pass
        
    if exported_count > 0:
      QMessageBox.information(self, "Success", "Exported %d frames to %s" % (exported_count, export_dir))
    else:
      QMessageBox.warning(self, "Warning", "No frames were successfully exported.")
      
  def export_all_forms(self):
    if self.sprite is None:
      return
      
    list_widget = self.type_to_list_widget.get(self.type)
    if list_widget is None:
      return
    row = list_widget.currentRow()
    if row < 0:
      return
      
    item_text = list_widget.item(row).text()
    entity_name = item_text[7:]
    clean_entity_name = "".join(c for c in entity_name if c.isalnum() or c in (' ', '_', '-')).strip()
    root_folder_name = "%03d - %s" % (row + 1, clean_entity_name)
    
    dir_path = QFileDialog.getExistingDirectory(self, "Select Directory to Export All Forms")
    if not dir_path:
      return
      
    export_dir = os.path.join(dir_path, root_folder_name)
    os.makedirs(export_dir, exist_ok=True)
    
    forms = Docs.get_all_forms_for_subtype("entity", self.type, self.subtype)
    exported_count = 0
    
    for other_form in forms:
      form_name = Docs.get_name_for_entity_form("entity", self.type, self.subtype, other_form)
      clean_form_name = "".join(c for c in form_name if c.isalnum() or c in (' ', '_', '-')).strip()
      form_folder_name = "%02X_%02X_%02X_%s" % (self.type, self.subtype, other_form, clean_form_name)
      form_dir = os.path.join(export_dir, form_folder_name)
      os.makedirs(form_dir, exist_ok=True)
      
      loading_data = SpriteLoadingData(self.type, self.subtype, other_form, self.rom)
      if loading_data.has_no_sprite:
        continue
        
      for frame_index in range(256):
        try:
          frame_image, x_off, y_off = self.renderer.render_entity_frame(loading_data, frame_index, (0, 0), [])
          if frame_image is not None:
            file_path = os.path.join(form_dir, "frame_%02X.png" % frame_index)
            frame_image.save(file_path)
            exported_count += 1
        except Exception:
          pass
          
    if exported_count > 0:
      QMessageBox.information(self, "Success", "Exported all forms to %s" % export_dir)
    else:
      QMessageBox.warning(self, "Warning", "No frames were successfully exported.")
