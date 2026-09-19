"""Create ready-to-upload CodeCanyon distribution ZIP archive."""
import os
import shutil
import zipfile


def create_codecanyon_package():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    dist_dir = os.path.join(base_dir, "codecanyon_package")
    zip_output_path = os.path.join(base_dir, "WhatsApp_Telegram_Number_Checker_v1.0.0_CodeCanyon.zip")

    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir, exist_ok=True)

    # 1. Copy Standalone Executable
    exe_src = os.path.join(base_dir, "dist", "WhatsApp_Telegram_Validator.exe")
    if os.path.exists(exe_src):
        shutil.copy2(exe_src, os.path.join(dist_dir, "WhatsApp_Telegram_Validator.exe"))
        print("[+] Copied executable")

    # 2. Copy documentation & samples
    shutil.copy2(os.path.join(base_dir, "Documentation.html"), os.path.join(dist_dir, "Documentation.html"))
    shutil.copy2(os.path.join(base_dir, "CODECANYON_USER_GUIDE.md"), os.path.join(dist_dir, "USER_GUIDE.md"))
    shutil.copy2(os.path.join(base_dir, "sample_apollo_leads.csv"), os.path.join(dist_dir, "sample_apollo_leads.csv"))
    shutil.copy2(os.path.join(base_dir, "logo.jpg"), os.path.join(dist_dir, "logo.jpg"))
    shutil.copy2(os.path.join(base_dir, "marketing_preview.jpg"), os.path.join(dist_dir, "marketing_preview.jpg"))
    print("[+] Copied documentation, graphics, and samples")

    # 3. Copy Source Code folder for Developer License
    src_folder = os.path.join(dist_dir, "Source_Code")
    os.makedirs(src_folder, exist_ok=True)
    shutil.copy2(os.path.join(base_dir, "app_gui.py"), os.path.join(src_folder, "app_gui.py"))
    shutil.copy2(os.path.join(base_dir, "build_exe.py"), os.path.join(src_folder, "build_exe.py"))
    shutil.copy2(os.path.join(base_dir, "requirements.txt"), os.path.join(src_folder, "requirements.txt"))
    shutil.copy2(os.path.join(base_dir, "logo.ico"), os.path.join(src_folder, "logo.ico"))
    shutil.copytree(os.path.join(base_dir, "src"), os.path.join(src_folder, "src"))
    print("[+] Copied clean source code")

    # 4. Create ZIP archive
    if os.path.exists(zip_output_path):
        os.remove(zip_output_path)

    print("\nCreating ZIP archive...")
    with zipfile.ZipFile(zip_output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(dist_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, dist_dir)
                zipf.write(abs_path, rel_path)

    zip_size_mb = os.path.getsize(zip_output_path) / (1024 * 1024)
    print(f"\n[SUCCESS] Created CodeCanyon release package ({zip_size_mb:.2f} MB):")
    print(zip_output_path)


if __name__ == "__main__":
    create_codecanyon_package()
