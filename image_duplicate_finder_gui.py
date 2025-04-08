import os
import shutil
import datetime
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import numpy as np

# 从原始文件导入哈希计算函数
from image_duplicate_finder import (
    calculate_dhash,
    calculate_phash,
    calculate_average_hash,
    hamming_distance,
    find_duplicate_images,
    copy_files_to_folders
)

class ImageDuplicateFinderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('图片查重工具')
        self.root.geometry('600x500')
        
        # 创建主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件夹选择
        ttk.Label(self.main_frame, text="图片文件夹路径:").grid(row=0, column=0, sticky=tk.W)
        self.folder_path = tk.StringVar()
        self.folder_entry = ttk.Entry(self.main_frame, textvariable=self.folder_path, width=50)
        self.folder_entry.grid(row=0, column=1, padx=5)
        ttk.Button(self.main_frame, text="浏览", command=self.browse_folder).grid(row=0, column=2)
        
        # 哈希方法选择
        ttk.Label(self.main_frame, text="哈希方法:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.hash_method = tk.StringVar(value="dhash")
        hash_frame = ttk.Frame(self.main_frame)
        hash_frame.grid(row=1, column=1, sticky=tk.W)
        ttk.Radiobutton(hash_frame, text="差值哈希 (dHash)", value="dhash", variable=self.hash_method).pack(side=tk.LEFT)
        ttk.Radiobutton(hash_frame, text="感知哈希 (pHash)", value="phash", variable=self.hash_method).pack(side=tk.LEFT)
        ttk.Radiobutton(hash_frame, text="平均哈希 (aHash)", value="ahash", variable=self.hash_method).pack(side=tk.LEFT)
        
        # 相似度阈值
        ttk.Label(self.main_frame, text="相似度阈值:").grid(row=2, column=0, sticky=tk.W)
        self.threshold = tk.StringVar(value="5")
        threshold_frame = ttk.Frame(self.main_frame)
        threshold_frame.grid(row=2, column=1, sticky=tk.W)
        self.threshold_scale = ttk.Scale(threshold_frame, from_=0, to=10, orient=tk.HORIZONTAL,
                                       variable=self.threshold, length=200)
        self.threshold_scale.pack(side=tk.LEFT)
        ttk.Label(threshold_frame, textvariable=self.threshold).pack(side=tk.LEFT, padx=5)
        
        # 输出文件夹
        ttk.Label(self.main_frame, text="输出文件夹:").grid(row=3, column=0, sticky=tk.W, pady=10)
        output_frame = ttk.Frame(self.main_frame)
        output_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W)
        
        self.unique_folder = tk.StringVar()
        self.duplicate_folder = tk.StringVar()
        
        ttk.Label(output_frame, text="唯一图片:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(output_frame, textvariable=self.unique_folder, width=30).grid(row=0, column=1, padx=5)
        ttk.Button(output_frame, text="浏览", command=lambda: self.browse_output_folder("unique")).grid(row=0, column=2)
        
        ttk.Label(output_frame, text="重复图片:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(output_frame, textvariable=self.duplicate_folder, width=30).grid(row=1, column=1, padx=5)
        ttk.Button(output_frame, text="浏览", command=lambda: self.browse_output_folder("duplicate")).grid(row=1, column=2)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(self.main_frame, length=400, mode='determinate',
                                      variable=self.progress_var)
        self.progress.grid(row=4, column=0, columnspan=3, pady=20)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(self.main_frame, textvariable=self.status_var)
        self.status_label.grid(row=5, column=0, columnspan=3)
        
        # 开始按钮
        self.start_button = ttk.Button(self.main_frame, text="开始查重", command=self.start_processing)
        self.start_button.grid(row=6, column=0, columnspan=3, pady=10)
        
        # 结果文本框
        self.result_text = tk.Text(self.main_frame, height=10, width=70)
        self.result_text.grid(row=7, column=0, columnspan=3, pady=10)
        
        # 设置列权重
        self.main_frame.columnconfigure(1, weight=1)
    
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            # 设置默认输出文件夹
            folder_name = os.path.basename(folder)
            self.unique_folder.set(os.path.join(folder, f"{folder_name}_unique"))
            self.duplicate_folder.set(os.path.join(folder, f"{folder_name}_duplicates"))
    
    def browse_output_folder(self, folder_type):
        folder = filedialog.askdirectory()
        if folder:
            if folder_type == "unique":
                self.unique_folder.set(folder)
            else:
                self.duplicate_folder.set(folder)
    
    def update_progress(self, value, status):
        self.progress_var.set(value)
        self.status_var.set(status)
        self.root.update_idletasks()
    
    def process_images(self):
        try:
            folder_path = self.folder_path.get()
            if not os.path.isdir(folder_path):
                messagebox.showerror("错误", "请选择有效的图片文件夹")
                return
            
            hash_method = self.hash_method.get()
            similarity_threshold = int(float(self.threshold.get()))
            unique_folder = self.unique_folder.get()
            duplicate_folder = self.duplicate_folder.get()
            
            self.update_progress(0, "正在查找重复图片...")
            duplicates = find_duplicate_images(folder_path, similarity_threshold, hash_method)
            
            if not duplicates:
                self.update_progress(100, "未找到重复图片")
                self.result_text.insert(tk.END, "未找到重复图片\n")
                return
            
            total_duplicates = sum(len(group) for group in duplicates)
            self.result_text.insert(tk.END, f"找到 {len(duplicates)} 组重复图片\n")
            self.result_text.insert(tk.END, f"共 {total_duplicates} 张重复图片\n")
            
            self.update_progress(50, "正在复制文件...")
            copied_files = copy_files_to_folders(duplicates, folder_path, unique_folder, duplicate_folder)
            
            self.update_progress(100, "处理完成")
            self.result_text.insert(tk.END, f"\n处理完成！\n")
            self.result_text.insert(tk.END, f"唯一图片已保存到: {unique_folder}\n")
            self.result_text.insert(tk.END, f"重复图片已保存到: {duplicate_folder}\n")
            
        except Exception as e:
            self.update_progress(0, f"错误: {str(e)}")
            messagebox.showerror("错误", str(e))
        finally:
            self.start_button.config(state=tk.NORMAL)
    
    def start_processing(self):
        self.start_button.config(state=tk.DISABLED)
        self.result_text.delete(1.0, tk.END)
        threading.Thread(target=self.process_images, daemon=True).start()
    
    def run(self):
        self.root.mainloop()

def main():
    app = ImageDuplicateFinderGUI()
    app.run()

if __name__ == "__main__":
    main()