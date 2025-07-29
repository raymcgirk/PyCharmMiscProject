import os
import time
import glob
import win32print
import subprocess

# === USER-DEFINED SETTINGS ===
PDF_FOLDER = r"C:\Your_folder"
WAIT_BETWEEN_PRINTS = 15  # seconds
WAIT_IF_NOT_READY = 30    # seconds
# =============================

# Printer status flags
PRINTER_STATUS_ERRORS = {
    0x00000002: "Out of Paper",
    0x00080000: "Out of Toner",
    0x00000008: "Paper Jam",
    0x00000010: "Paper Out",
    0x00000020: "Manual Feed",
    0x00000200: "Offline",
    0x00400000: "Error"
}

def printer_is_ready(printer_name):
    hPrinter = win32print.OpenPrinter(printer_name)
    try:
        printer_info = win32print.GetPrinter(hPrinter, 2)
        status = printer_info["Status"]
        if status == 0:
            return True
        else:
            for flag, msg in PRINTER_STATUS_ERRORS.items():
                if status & flag:
                    print(f"Printer status: {msg}")
            return False
    finally:
        win32print.ClosePrinter(hPrinter)

# Get all PDF files and sort alphabetically by filename
pdf_files = glob.glob(os.path.join(PDF_FOLDER, "*.pdf"))
pdf_files.sort(key=lambda x: os.path.basename(x).lower())

if not pdf_files:
    print(f"No PDF files found in: {PDF_FOLDER}")
    exit()

printers = [p[2] for p in win32print.EnumPrinters(2)]
print("Available printers:")
for idx, name in enumerate(printers, 1):
    print(f"{idx}: {name}")

choice = input("Select printer number (or press Enter for default): ").strip()
if choice.isdigit():
    printer_name = printers[int(choice) - 1]
else:
    printer_name = win32print.GetDefaultPrinter()

print(f"Using printer: {printer_name}")

sumatra_path = r"C:\Tools\SumatraPDF-3.5.2-64.exe"
if not os.path.exists(sumatra_path):
    print(f"Error: SumatraPDF not found at {sumatra_path}")
    exit(1)

for pdf_file in pdf_files:
    print(f"Preparing to print: {os.path.basename(pdf_file)}")

    while not printer_is_ready(printer_name):
        print("Waiting for printer to become ready...")
        time.sleep(WAIT_IF_NOT_READY)

    try:
        cmd = [
            sumatra_path,
            "-print-to", printer_name,
            pdf_file
        ]

        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error printing {os.path.basename(pdf_file)}: {result.stderr.strip()}")
        else:
            print(f"Sent to printer: {os.path.basename(pdf_file)}")
    except Exception as e:
        print(f"Error printing {os.path.basename(pdf_file)}: {e}")

    time.sleep(WAIT_BETWEEN_PRINTS)
