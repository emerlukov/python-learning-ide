# managers/emergency_recovery.py
"""
Emergency recovery after crash
"""
import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.metrics import dp

from ide_core.themes import ThemeManager
from utils.paths import user_data_path, ensure_user_data_dir


class EmergencyRecovery:
    """Восстановление данных после аварийного закрытия"""

    def __init__(self, app):
        self.app = app
        ensure_user_data_dir()
        self._emergency_path = user_data_path('emergency_backup.py')

    def check_and_restore(self):
        """Проверяет наличие emergency бэкапа и предлагает восстановить"""
        Clock.schedule_once(self._check_emergency_backup, 0.5)

    def _check_emergency_backup(self, dt):
        """Проверяет, есть ли emergency бэкап"""
        if not os.path.exists(self._emergency_path):
            return

        try:
            with open(self._emergency_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()

            if backup_content.strip() and backup_content != self.app.code_input.text:
                self._show_restore_dialog(backup_content)
        except:
            pass

    def _show_restore_dialog(self, backup_content):
        """Показывает диалог восстановления"""
        tr = self.app.tr
        theme = ThemeManager.get_theme()

        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(
            text=tr.get('recovery_message', 'Unsaved code found after crash.\nRestore?'),
            color=theme['text_color'], font_size=dp(12), halign='center',
            size_hint_y=None, height=dp(50)
        ))

        btn_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))

        popup = Popup(
            title=tr.get('recovery_title', 'Data Recovery'),
            title_color=theme['popup_title'], background='',
            background_color=theme.get('popup_bg', (0.188, 0.204, 0.251, 1)),
            content=content, size_hint=(0.8, 0.3), auto_dismiss=False
        )

        def on_restore(btn):
            self.app.code_input.text = backup_content
            if hasattr(self.app, 'editor'):
                self.app.editor.original_lines = backup_content.split('\n')
                self.app.editor._update_line_panel()

            try:
                os.remove(self._emergency_path)
            except:
                pass

            popup.dismiss()
            self.app.show_result_popup(tr.get('code_restored', 'Code restored'))

        def on_ignore(btn):
            try:
                os.remove(self._emergency_path)
            except:
                pass
            popup.dismiss()

        btn_restore = Button(
            text=tr.get('recovery_restore', 'Restore'), font_name='SourceBold',
            background_color=(0.2, 0.5, 0.2, 1), background_normal='', background_down='',
            color=(1, 1, 1, 1), on_release=on_restore
        )

        btn_ignore = Button(
            text=tr.get('recovery_ignore', 'Ignore'), font_name='SourceBold',
            background_color=theme['widget_bg'], background_normal='', background_down='',
            color=theme['text_color'], on_release=on_ignore
        )

        btn_layout.add_widget(btn_restore)
        btn_layout.add_widget(btn_ignore)
        content.add_widget(btn_layout)

        if hasattr(self.app, 'wrap_widget_buttons'):
            self.app.wrap_widget_buttons(content)

        popup.open()

    def save_emergency_backup(self, content):
        """Сохраняет emergency бэкап"""
        try:
            os.makedirs(os.path.dirname(self._emergency_path), exist_ok=True)
            with open(self._emergency_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except:
            pass