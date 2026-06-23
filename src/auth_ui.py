import os
import re
import secrets
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional
from auth_db import AuthDB
from face_detection import FaceDetectionWindow


class AuthApp:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or Path(__file__).resolve().parent)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = AuthDB(str(self.data_dir / 'auth.db'))
        self.root = tk.Tk()
        self.root.title('SecureChat 登录 / 注册')
        self.root.geometry('520x520')
        self.root.minsize(480, 460)
        self.root.resizable(True, True)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self._build_ui()

    def run(self):
        self.root.mainloop()

    def _build_ui(self):
        self._active_frame = None
        self._error_var = tk.StringVar()

        header = tk.Label(
            self.root,
            text='SecureChat 账号系统',
            font=('Segoe UI', 20, 'bold'),
            pady=18
        )
        header.pack()

        self._tab_frame = tk.Frame(self.root, pady=10)
        self._tab_frame.pack()

        self._login_button = tk.Button(
            self._tab_frame, text='登录', width=12,
            command=self._show_login_frame
        )
        self._login_button.pack(side='left', padx=8)

        self._register_button = tk.Button(
            self._tab_frame, text='注册', width=12,
            command=self._show_register_frame
        )
        self._register_button.pack(side='left', padx=8)

        self._error_label = tk.Label(
            self.root, textvariable=self._error_var,
            fg='#d9534f', font=('Segoe UI', 10), wraplength=460,
            justify='center'
        )
        self._error_label.pack(pady=(4, 0))

        self._canvas_frame = tk.Frame(self.root)
        self._canvas_frame.pack(fill='both', expand=True, pady=16)

        self._canvas = tk.Canvas(
            self._canvas_frame, borderwidth=0, highlightthickness=0
        )
        self._v_scroll = tk.Scrollbar(
            self._canvas_frame, orient='vertical', command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._v_scroll.set)
        self._v_scroll.pack(side='right', fill='y')
        self._canvas.pack(side='left', fill='both', expand=True)

        self._frame_container = tk.Frame(self._canvas)
        self._canvas.create_window((0, 0), window=self._frame_container, anchor='nw')
        self._frame_container.bind(
            '<Configure>',
            lambda event: self._canvas.configure(scrollregion=self._canvas.bbox('all'))
        )
        self._canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        self._build_login_frame()
        self._build_register_frame()
        self._show_login_frame()

    def _clear_error(self):
        self._error_var.set('')

    def _set_error(self, message: str):
        self._error_var.set(message)

    def _show_login_frame(self):
        self._switch_frame(self._login_frame)
        self._login_button.config(relief='sunken')
        self._register_button.config(relief='raised')
        self._clear_error()

    def _show_register_frame(self):
        self._switch_frame(self._register_frame)
        self._register_button.config(relief='sunken')
        self._login_button.config(relief='raised')
        self._clear_error()

    def _switch_frame(self, frame):
        if self._active_frame:
            self._active_frame.pack_forget()
        self._active_frame = frame
        self._active_frame.pack(fill='both', expand=True)

    def _build_login_frame(self):
        self._login_frame = tk.Frame(self._frame_container)

        self._login_phone = self._make_input(self._login_frame, '手机号')
        self._login_password = self._make_input(
            self._login_frame, '密码', show='*'
        )
        self._login_password_visible = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self._login_frame, text='显示密码', variable=self._login_password_visible,
            command=self._toggle_login_password, font=('Segoe UI', 9)
        ).pack(pady=(0, 8), padx=40, anchor='w')
        self._login_code = self._make_input(self._login_frame, '验证码')

        login_button = tk.Button(
            self._login_frame, text='登录', width=20,
            bg='#4a90e2', fg='white', command=self._handle_login
        )
        login_button.pack(pady=20)

        hint = tk.Label(
            self._login_frame,
            text='请输入手机号、密码和验证码进行登录。',
            font=('Segoe UI', 10), fg='#555555'
        )
        hint.pack(pady=(10, 0))

        clear_button = tk.Button(
            self._login_frame, text='清空数据库', width=20,
            bg='#f0ad4e', fg='white', command=self._handle_clear_database
        )
        clear_button.pack(pady=(10, 0))

    def _build_register_frame(self):
        self._register_frame = tk.Frame(self._frame_container)

        self._reg_phone = self._make_input(
            self._register_frame, '手机号'
        )
        self._reg_password = self._make_input(
            self._register_frame, '密码', show='*'
        )
        self._reg_password_visible = tk.BooleanVar(value=False)
        tk.Checkbutton(
            self._register_frame, text='显示密码', variable=self._reg_password_visible,
            command=self._toggle_register_password, font=('Segoe UI', 9)
        ).pack(pady=(0, 8), padx=40, anchor='w')
        self._reg_full_name = self._make_input(
            self._register_frame, '真实姓名'
        )
        self._reg_id_card = self._make_input(
            self._register_frame, '身份证号'
        )
        self._reg_code = self._make_input(self._register_frame, '验证码')

        self._reg_code_label = tk.Label(
            self._register_frame, text='生成的验证码会显示在这里。',
            font=('Segoe UI', 10), fg='#555555', wraplength=360, justify='left'
        )
        self._reg_code_label.pack(pady=(0, 10), padx=40)

        generate_code_button = tk.Button(
            self._register_frame, text='生成验证码', width=20,
            bg='#5cb85c', fg='white', command=self._generate_registration_code
        )
        generate_code_button.pack(pady=(0, 14))

        register_button = tk.Button(
            self._register_frame, text='注册账号', width=20,
            bg='#d9534f', fg='white', command=self._handle_register
        )
        register_button.pack(pady=10)

    def _make_input(self, parent, label_text: str, show: str = '') -> tk.Entry:
        frame = tk.Frame(parent)
        frame.pack(fill='x', padx=40, pady=6)
        label = tk.Label(frame, text=label_text, anchor='w',
                         font=('Segoe UI', 10))
        label.pack(fill='x')
        entry = tk.Entry(frame, show=show, font=('Segoe UI', 11))
        entry.pack(fill='x', pady=(4, 0), ipady=8)
        return entry

    def _toggle_login_password(self):
        self._login_password.config(
            show='' if self._login_password_visible.get() else '*'
        )

    def _toggle_register_password(self):
        self._reg_password.config(
            show='' if self._reg_password_visible.get() else '*'
        )

    def _generate_registration_code(self):
        phone = self._reg_phone.get().strip()
        if not phone:
            self._set_error('请输入手机号以生成验证码。')
            return
        if not re.fullmatch(r'[0-9+\- ]{7,20}', phone):
            self._set_error('请输入有效手机号格式。')
            return
        self._clear_error()
        code = f"{secrets.randbelow(1000000):06d}"
        self._pending_registration_code = code
        self._reg_code_label.config(text=f'当前验证码：{code}（请填写到上方验证码框）')

    def _handle_register(self):
        phone = self._reg_phone.get().strip()
        password = self._reg_password.get().strip()
        full_name = self._reg_full_name.get().strip()
        id_card = self._reg_id_card.get().strip()
        code = self._reg_code.get().strip()

        if not phone or not password or not full_name or not id_card or not code:
            self._set_error('请填写手机号、密码、真实姓名、身份证号，并输入验证码。')
            return
        if len(password) < 6:
            self._set_error('密码长度至少6位。')
            return
        if not re.fullmatch(r'[0-9+\- ]{7,20}', phone):
            self._set_error('请输入有效手机号格式。')
            return
        if not re.fullmatch(r'[0-9Xx0-9]{15,18}', id_card.replace(' ', '')):
            self._set_error('请输入有效身份证号。')
            return
        if not hasattr(self, '_pending_registration_code') or code != self._pending_registration_code:
            self._set_error('验证码错误，请先生成并填写正确验证码。')
            return

        self._clear_error()
        try:
            self.db.create_user(phone, password, full_name, id_card, code)
        except Exception as e:
            self._set_error(f'注册失败：{e}')
            return

        messagebox.showinfo('注册成功', f'账号已创建，验证码已保存为：{code}\n请在登录时使用该验证码。')
        self._clear_register_form()
        self._show_login_frame()

    def _clear_register_form(self):
        self._reg_phone.delete(0, tk.END)
        self._reg_password.delete(0, tk.END)
        self._reg_full_name.delete(0, tk.END)
        self._reg_id_card.delete(0, tk.END)
        self._reg_code.delete(0, tk.END)
        self._pending_registration_code = None
        self._reg_code_label.config(text='生成的验证码会显示在这里。')

    def _handle_login(self):
        phone = self._login_phone.get().strip()
        password = self._login_password.get().strip()
        code = self._login_code.get().strip()

        if not phone or not password or not code:
            self._set_error('请填写手机号、密码和验证码进行登录。')
            return
        if not re.fullmatch(r'[0-9+\- ]{7,20}', phone):
            self._set_error('请输入有效手机号格式。')
            return

        if not self.db.verify_password(phone, password):
            self._set_error('手机号或密码不正确。')
            return
        if not self.db.verify_code(phone, code):
            self._set_error('验证码错误或已过期。')
            return

        self._clear_error()
        self._finish_login(phone)

    def _finish_login(self, phone: str):
        self._login_phone.delete(0, tk.END)
        self._login_password.delete(0, tk.END)
        self._login_code.delete(0, tk.END)
        self._show_home(phone)

    def _show_home(self, phone: str):
        self._switch_frame(self._home_frame(phone))
        self._login_button.config(state='disabled')
        self._register_button.config(state='disabled')

    def _home_frame(self, phone: str):
        frame = tk.Frame(self._frame_container)
        user = self.db.get_user(phone)
        tk.Label(
            frame, text=f'欢迎，{user["full_name"]}！',
            font=('Segoe UI', 16, 'bold')
        ).pack(pady=20)
        tk.Label(
            frame, text=f'当前登录手机号：{phone}',
            font=('Segoe UI', 12)
        ).pack(pady=(0, 12))
        tk.Label(
            frame, text=f'身份证号：{user["id_card"]}',
            font=('Segoe UI', 11)
        ).pack(pady=(0, 10))

        camera_button = tk.Button(
            frame, text='启动摄像头人脸检测', width=18,
            bg='#5cb85c', fg='white',
            command=lambda: FaceDetectionWindow(self.root, phone, user["full_name"])
        )
        camera_button.pack(pady=12)

        tk.Button(
            frame, text='退出登录', width=18,
            bg='#777777', fg='white', command=self._logout
        ).pack(pady=24)
        return frame

    def _handle_clear_database(self):
        confirm = messagebox.askyesno(
            '确认清空',
            '该操作将删除所有用户数据，且不可恢复。是否继续？'
        )
        if not confirm:
            return
        self.db.clear_database()
        self._clear_error()
        self._login_phone.delete(0, tk.END)
        self._login_password.delete(0, tk.END)
        self._login_code.delete(0, tk.END)
        messagebox.showinfo('已清空', '数据库已清空，所有账号已删除。')

    def _logout(self):
        self._login_button.config(state='normal')
        self._register_button.config(state='normal')
        self._show_login_frame()
        self._clear_error()

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _on_close(self):
        try:
            self.db.conn.close()
        except Exception:
            pass
        self.root.destroy()
