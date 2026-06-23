"""
人脸检测模块 - 调用摄像头并检测人脸
"""

import cv2
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading


class FaceDetectionWindow:
    """摄像头人脸检测窗口"""
    
    def __init__(self, parent, phone: str, user_name: str):
        self.phone = phone
        self.user_name = user_name
        self.running = True
        
        # 创建新窗口
        self.window = tk.Toplevel(parent)
        self.window.title(f'人脸检测 - {user_name}')
        self.window.geometry('800x600')
        self.window.protocol('WM_DELETE_WINDOW', self._on_close)
        
        # 加载级联分类器进行人脸检测
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # 创建标签用于显示摄像头画面
        self.label = tk.Label(self.window, bg='black')
        self.label.pack(fill='both', expand=True)
        
        # 创建按钮框
        button_frame = tk.Frame(self.window)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.status_label = tk.Label(
            button_frame, text='正在初始化摄像头...',
            font=('Segoe UI', 11), fg='#4a90e2'
        )
        self.status_label.pack(side='left', padx=5)
        
        close_button = tk.Button(
            button_frame, text='关闭摄像头',
            bg='#d9534f', fg='white', command=self._on_close
        )
        close_button.pack(side='right', padx=5)
        
        # 启动摄像头线程
        self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self.camera_thread.start()
    
    def _camera_loop(self):
        """摄像头主循环"""
        cap = None
        try:
            # 打开摄像头
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 800)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
            cap.set(cv2.CAP_PROP_FPS, 30)
            
            if not cap.isOpened():
                self._update_status('摄像头打开失败', is_error=True)
                return
            
            self._update_status('摄像头已启动，正在检测人脸...')
            face_count = 0
            
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 翻转画面（镜像效果）
                frame = cv2.flip(frame, 1)
                
                # 转换为灰度图
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 检测人脸
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                
                # 用红色框圈出人脸
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                    # 在人脸上方显示"人脸已检测"
                    cv2.putText(frame, 'Face Detected', (x, y - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # 检测到的人脸数
                current_face_count = len(faces)
                if current_face_count > 0 and current_face_count != face_count:
                    face_count = current_face_count
                    self._update_status(f'已检测到 {face_count} 张人脸')
                elif current_face_count == 0 and face_count > 0:
                    face_count = 0
                    self._update_status('摄像头已启动，正在检测人脸...')
                
                # 转换为RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 转换为PIL Image
                image = Image.fromarray(frame_rgb)
                
                # 转换为PhotoImage
                photo = ImageTk.PhotoImage(image)
                
                # 更新标签
                self.label.config(image=photo)
                self.label.image = photo
                
                # 更新窗口
                self.window.update()
                
        except Exception as e:
            self._update_status(f'错误：{str(e)}', is_error=True)
        finally:
            if cap:
                cap.release()
    
    def _update_status(self, message: str, is_error: bool = False):
        """更新状态标签"""
        try:
            color = '#d9534f' if is_error else '#5cb85c'
            self.status_label.config(text=message, fg=color)
            self.window.update()
        except:
            pass
    
    def _on_close(self):
        """关闭窗口"""
        self.running = False
        try:
            self.window.destroy()
        except:
            pass
