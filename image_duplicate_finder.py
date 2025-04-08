import os
import shutil
import hashlib
import datetime
from PIL import Image
import numpy as np
from pathlib import Path


def calculate_dhash(image, hash_size=8):
    """
    计算图像的差值哈希(dHash)
    """
    # 调整图像大小并转换为灰度
    image = image.convert('L').resize((hash_size + 1, hash_size))
    pixels = list(image.getdata())
    
    # 计算差值哈希
    diff = []
    for row in range(hash_size):
        for col in range(hash_size):
            pixel_idx = row * (hash_size + 1) + col
            diff.append(pixels[pixel_idx] > pixels[pixel_idx + 1])
    
    # 将布尔值转换为整数并打包成十六进制字符串
    decimal_value = 0
    for bit in diff:
        decimal_value = (decimal_value << 1) | bit
    
    return format(decimal_value, f'0{hash_size**2//4}x')


def calculate_phash(image, hash_size=8):
    """
    计算图像的感知哈希(pHash)
    """
    # 调整图像大小并转换为灰度
    image = image.convert('L').resize((hash_size, hash_size))
    pixels = np.array(image.getdata()).reshape((hash_size, hash_size))
    
    # 计算DCT
    dct = np.zeros((hash_size, hash_size))
    for i in range(hash_size):
        for j in range(hash_size):
            dct[i, j] = pixels[i, j]
    
    # 计算平均值（不包括第一个元素）
    avg = (dct.sum() - dct[0, 0]) / (hash_size * hash_size - 1)
    
    # 生成哈希
    hash_bits = (dct >= avg).flatten()
    
    # 将布尔值转换为整数并打包成十六进制字符串
    decimal_value = 0
    for bit in hash_bits:
        decimal_value = (decimal_value << 1) | bit
    
    return format(decimal_value, f'0{hash_size**2//4}x')


def calculate_average_hash(image, hash_size=8):
    """
    计算图像的平均哈希(aHash)
    """
    # 调整图像大小并转换为灰度
    image = image.convert('L').resize((hash_size, hash_size))
    pixels = list(image.getdata())
    
    # 计算平均值
    avg = sum(pixels) / len(pixels)
    
    # 生成哈希
    hash_bits = [pixel >= avg for pixel in pixels]
    
    # 将布尔值转换为整数并打包成十六进制字符串
    decimal_value = 0
    for bit in hash_bits:
        decimal_value = (decimal_value << 1) | bit
    
    return format(decimal_value, f'0{hash_size**2//4}x')


def hamming_distance(hash1, hash2):
    """
    计算两个哈希值之间的汉明距离
    """
    h1 = int(hash1, 16)
    h2 = int(hash2, 16)
    return bin(h1 ^ h2).count('1')


def find_duplicate_images(folder_path, similarity_threshold=5, hash_method='dhash'):
    """
    在指定文件夹中查找重复图片
    
    参数:
    folder_path: 图片文件夹路径
    similarity_threshold: 相似度阈值，汉明距离小于此值的图片被视为重复
    hash_method: 使用的哈希方法 ('dhash', 'phash', 'ahash')
    
    返回:
    duplicates: 重复图片组的列表
    """
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    
    # 存储图片路径和对应的哈希值
    images = []
    
    # 遍历文件夹中的所有文件
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            if file_ext in image_extensions:
                try:
                    with Image.open(file_path) as img:
                        # 根据选择的方法计算哈希
                        if hash_method == 'dhash':
                            img_hash = calculate_dhash(img)
                        elif hash_method == 'phash':
                            img_hash = calculate_phash(img)
                        elif hash_method == 'ahash':
                            img_hash = calculate_average_hash(img)
                        else:
                            img_hash = calculate_dhash(img)  # 默认使用dhash
                        
                        images.append((file_path, img_hash))
                except Exception as e:
                    print(f"无法处理图片 {file_path}: {e}")
    
    print(f"已处理 {len(images)} 张图片")
    
    # 查找重复图片
    duplicates = []
    processed = set()
    
    for i, (img1_path, img1_hash) in enumerate(images):
        if img1_path in processed:
            continue
        
        duplicate_group = [img1_path]
        
        for j, (img2_path, img2_hash) in enumerate(images):
            if i != j and img2_path not in processed:
                distance = hamming_distance(img1_hash, img2_hash)
                if distance <= similarity_threshold:
                    duplicate_group.append(img2_path)
                    processed.add(img2_path)
        
        if len(duplicate_group) > 1:  # 只有当找到重复时才添加到结果中
            duplicates.append(duplicate_group)
            processed.add(img1_path)
    
    return duplicates


def copy_files_to_folders(duplicates, folder_path, unique_folder, duplicate_folder):
    """
    将图片复制到两个不同的文件夹：一个存放不重复的图片，一个存放重复的图片
    
    参数:
    duplicates: 重复图片组的列表
    folder_path: 原始图片文件夹路径
    unique_folder: 不重复图片的输出文件夹路径
    duplicate_folder: 重复图片的输出文件夹路径
    
    返回:
    copied_files: 复制的文件记录字典
    """
    # 创建输出文件夹
    if not os.path.exists(unique_folder):
        os.makedirs(unique_folder)
    if not os.path.exists(duplicate_folder):
        os.makedirs(duplicate_folder)
    
    # 创建记录文件
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = os.path.join(os.path.dirname(unique_folder), f"image_copy_log_{timestamp}.txt")
    
    copied_files = {}
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        log_file.write(f"图片处理记录 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("=" * 80 + "\n\n")
        
        # 记录重复图片组并处理复制
        log_file.write("重复图片组处理:\n")
        unique_count = 0
        duplicate_count = 0
        
        for i, group in enumerate(duplicates, 1):
            log_file.write(f"  重复组 #{i} (共 {len(group)} 张图片):\n")
            
            # 第一张图片复制到unique文件夹
            original_img = group[0]
            filename = os.path.basename(original_img)
            unique_dest = os.path.join(unique_folder, filename)
            
            # 处理文件名冲突
            counter = 1
            base, ext = os.path.splitext(filename)
            while os.path.exists(unique_dest):
                unique_dest = os.path.join(unique_folder, f"{base}_{counter}{ext}")
                counter += 1
            
            try:
                shutil.copy2(original_img, unique_dest)
                copied_files[original_img] = unique_dest
                log_file.write(f"    保留为唯一图片: {original_img} -> {unique_dest}\n")
                unique_count += 1
            except Exception as e:
                log_file.write(f"    无法复制唯一图片 {original_img}: {e}\n")
            
            # 其余图片复制到duplicates文件夹
            for duplicate_img in group[1:]:
                filename = os.path.basename(duplicate_img)
                dup_dest = os.path.join(duplicate_folder, filename)
                
                # 处理文件名冲突
                counter = 1
                base, ext = os.path.splitext(filename)
                while os.path.exists(dup_dest):
                    dup_dest = os.path.join(duplicate_folder, f"{base}_{counter}{ext}")
                    counter += 1
                
                try:
                    shutil.copy2(duplicate_img, dup_dest)
                    copied_files[duplicate_img] = dup_dest
                    log_file.write(f"    标记为重复: {duplicate_img} -> {dup_dest}\n")
                    duplicate_count += 1
                except Exception as e:
                    log_file.write(f"    无法复制重复图片 {duplicate_img}: {e}\n")
            
            log_file.write("\n")
        
        # 复制其他非重复图片到唯一文件夹
        log_file.write("\n复制其他非重复图片:\n")
        all_processed_paths = {img for group in duplicates for img in group}
        
        # 遍历文件夹中的所有文件
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # 只处理图片文件且不在已处理列表中的文件
                if file_ext in image_extensions and file_path not in all_processed_paths:
                    filename = os.path.basename(file_path)
                    destination = os.path.join(unique_folder, filename)
                    
                    # 处理文件名冲突
                    counter = 1
                    base, ext = os.path.splitext(filename)
                    while os.path.exists(destination):
                        destination = os.path.join(unique_folder, f"{base}_{counter}{ext}")
                        counter += 1
                    
                    try:
                        shutil.copy2(file_path, destination)
                        copied_files[file_path] = destination
                        log_file.write(f"  {file_path} -> {destination}\n")
                        unique_count += 1
                    except Exception as e:
                        log_file.write(f"  无法复制 {file_path}: {e}\n")
        
        # 写入摘要信息
        log_file.write("\n" + "=" * 80 + "\n")
        log_file.write(f"摘要:\n")
        log_file.write(f"- 发现 {len(duplicates)} 组重复图片，共 {duplicate_count} 张重复图片已复制到 {duplicate_folder}\n")
        log_file.write(f"- 共 {unique_count} 张非重复图片已复制到 {unique_folder}\n")
    
    print(f"重复图片已复制到 {duplicate_folder}")
    print(f"非重复图片已复制到 {unique_folder}")
    print(f"详细记录已保存到 {log_file_path}")
    
    return copied_files


def main():
    # 获取用户输入
    folder_path = input("请输入图片文件夹路径: ")
    
    # 验证文件夹路径
    if not os.path.isdir(folder_path):
        print(f"错误: 路径 '{folder_path}' 不是有效的文件夹")
        return
    
    # 选择哈希方法
    print("\n选择图像哈希方法:")
    print("1. 差值哈希 (dHash) - 默认，对图像变化敏感")
    print("2. 感知哈希 (pHash) - 对图像内容变化敏感")
    print("3. 平均哈希 (aHash) - 计算简单但准确度较低")
    hash_choice = input("请选择 (1-3，默认为1): ").strip() or "1"
    
    hash_methods = {"1": "dhash", "2": "phash", "3": "ahash"}
    hash_method = hash_methods.get(hash_choice, "dhash")
    
    # 设置相似度阈值
    threshold_input = input("\n请输入相似度阈值 (0-10，默认为5，值越小要求越严格): ").strip() or "5"
    try:
        similarity_threshold = int(threshold_input)
        if similarity_threshold < 0 or similarity_threshold > 10:
            print("阈值超出范围，使用默认值5")
            similarity_threshold = 5
    except ValueError:
        print("无效的阈值，使用默认值5")
        similarity_threshold = 5
    
    # 设置输出文件夹
    parent_dir = os.path.dirname(folder_path)
    folder_name = os.path.basename(folder_path)
    default_unique = os.path.join(parent_dir, f"{folder_name}_unique")
    default_duplicate = os.path.join(parent_dir, f"{folder_name}_duplicates")
    
    unique_folder = input(f"\n请输入不重复图片的输出文件夹路径 (默认: {default_unique}): ").strip() or default_unique
    duplicate_folder = input(f"请输入重复图片的输出文件夹路径 (默认: {default_duplicate}): ").strip() or default_duplicate
    
    print("\n开始查找重复图片...")
    duplicates = find_duplicate_images(folder_path, similarity_threshold, hash_method)
    
    if not duplicates:
        print("未找到重复图片")
        return
    
    print(f"\n找到 {len(duplicates)} 组重复图片")
    print(f"共 {sum(len(group) for group in duplicates)} 张重复图片")
    
    # 确认是否复制文件
    confirm = input("\n是否将图片分类复制到新文件夹? (y/n): ").strip().lower()
    if confirm == 'y':
        copy_files_to_folders(duplicates, folder_path, unique_folder, duplicate_folder)
    else:
        print("操作已取消")


if __name__ == "__main__":
    main()
