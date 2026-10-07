"""
DClean Unified Launcher.

Acts as the single entrypoint for the desktop shortcut, Windows context menu,
and command-line usage. Automatically discovers dashboard modules if present,
or provides a lightweight, responsive desktop GUI and headless one-click cleaner.
"""

import os
import sys
import argparse
import subprocess
from typing import Optional

# Force Streamlit to production mode (prevents developmentMode from defaulting to True in PyInstaller)
os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
os.environ["STREAMLIT_SERVER_PORT"] = "8501"
os.environ["STREAMLIT_BROWSER_SERVER_PORT"] = "8501"
os.environ["STREAMLIT_SERVER_HEADLESS"] = "false"

# Ensure project root is in sys.path (supports both source execution and PyInstaller frozen bundle)
if getattr(sys, "frozen", False):
    PROJECT_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def run_headless_clean(file_path: str, contract_path: Optional[str] = None) -> bool:
    """
    Executes cleaning on a single file headless (used for Windows right-click context menu).
    Opens the output directory upon completion and displays a status dialog.
    """
    from pipeline.runner import PipelineRunner

    if not os.path.exists(file_path):
        print(f"[Error] Target file does not exist: {file_path}")
        return False

    base_dir = os.path.dirname(os.path.abspath(file_path))
    file_stem = os.path.splitext(os.path.basename(file_path))[0]
    out_excel = os.path.join(base_dir, f"{file_stem}_Cleaned.xlsx")
    out_db = os.path.join(base_dir, f"{file_stem}_Cleaned.db")

    print(f"[DClean] Cleaning file: {file_path}")
    print(f"[DClean] Contract: {contract_path or 'Auto-Detect (Local NLP Classifier)'}")
    
    try:
        runner = PipelineRunner(contract_path=contract_path, db_path=out_db)
        summary = runner.run(input_file_path=file_path, output_excel_path=out_excel)
    except Exception as e:
        err_msg = f"DClean encountered an error while processing:\n\n{os.path.basename(file_path)}\n\nDetails: {e}"
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("DClean - Processing Error", err_msg)
        except Exception:
            print(err_msg)
        return False

    msg = (
        f"DClean Processing Complete!\n\n"
        f"File: {os.path.basename(file_path)}\n"
        f"Total Ingested: {summary.total_rows} rows\n"
        f"Cleaned Valid: {summary.valid_rows} rows\n"
        f"Quarantined: {summary.quarantined_rows} ({summary.quarantine_rate_pct}%)\n"
        f"Unique Entities: {summary.unique_persons_resolved}\n"
        f"Merged Duplicates: {summary.duplicate_events_merged}\n"
        f"Health Status: {summary.status}\n\n"
        f"Cleaned Excel: {out_excel}"
    )

    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("DClean - Success", msg)
        # Open explorer to the folder
        os.startfile(base_dir)
    except Exception:
        print(msg)

    return True

def launch_streamlit_direct() -> bool:
    """
    Launches the modern Streamlit studio directly in-process, opens default browser,
    hides any terminal window, and automatically shuts down when the browser tab is closed.
    """
    candidates = [
        os.path.join(PROJECT_ROOT, "dashboard.py"),
        os.path.join(PROJECT_ROOT, "_internal", "dashboard.py"),
        os.path.join(os.path.dirname(sys.executable), "dashboard.py"),
        os.path.join(os.path.dirname(sys.executable), "_internal", "dashboard.py"),
        os.path.join(PROJECT_ROOT, "dashboard", "app.py"),
        os.path.join(PROJECT_ROOT, "app.py")
    ]
    target_dashboard = None
    for c in candidates:
        if os.path.exists(c):
            target_dashboard = c
            break

    if not target_dashboard:
        return False

    try:
        import threading
        import time
        from streamlit.web import bootstrap

        # Fix 404 Not Found in PyInstaller frozen mode:
        # streamlit.file_util.get_static_dir() looks inside the PYZ/zip where os.path.isdir() is False.
        # We redirect it to the extracted static asset directory in _internal/streamlit/static.
        try:
            import streamlit.file_util as fu
            static_candidates = [
                os.path.join(getattr(sys, "_MEIPASS", ""), "streamlit", "static"),
                os.path.join(os.path.dirname(sys.executable), "_internal", "streamlit", "static"),
                os.path.join(os.path.dirname(sys.executable), "streamlit", "static"),
                os.path.join(PROJECT_ROOT, "streamlit", "static"),
                os.path.join(PROJECT_ROOT, "_internal", "streamlit", "static"),
            ]
            for sc in static_candidates:
                if sc and os.path.isdir(sc):
                    real_static = os.path.abspath(sc)
                    fu.get_static_dir = lambda: real_static
                    break
        except Exception:
            pass

        def monitor_tab_close():
            from streamlit.runtime.runtime import Runtime, RuntimeState

            # Wait for runtime initialization
            while not Runtime.exists():
                time.sleep(0.5)

            # Wait up to 120s for the browser to open and connect
            connected_once = False
            start_wait = time.time()
            while time.time() - start_wait < 120:
                time.sleep(0.5)
                if not Runtime.exists():
                    return
                if Runtime.instance().state == RuntimeState.ONE_OR_MORE_SESSIONS_CONNECTED:
                    connected_once = True
                    break

            if not connected_once:
                # Browser never connected within 120 seconds
                os._exit(0)

            # Once connected, monitor for tab closure
            disconnect_time = None
            while True:
                time.sleep(1)
                if not Runtime.exists():
                    return
                state = Runtime.instance().state
                if state == RuntimeState.ONE_OR_MORE_SESSIONS_CONNECTED:
                    disconnect_time = None
                elif state == RuntimeState.NO_SESSIONS_CONNECTED:
                    if disconnect_time is None:
                        disconnect_time = time.time()
                    elif time.time() - disconnect_time >= 4.0:
                        # 4 second grace period for page refresh (F5)
                        os._exit(0)

        # Start browser tab monitor thread
        watcher = threading.Thread(target=monitor_tab_close, daemon=True)
        watcher.start()

        # Explicitly open browser tab via Windows Shell (100% reliable in GUI apps)
        def auto_open_browser():
            time.sleep(1.2)
            url = "http://localhost:8501"
            try:
                os.startfile(url)
            except Exception:
                import webbrowser
                webbrowser.open(url)

        threading.Thread(target=auto_open_browser, daemon=True).start()

        # Lightweight redirect server for port 3000 in case user opens http://localhost:3000
        def run_port_3000_redirect():
            import http.server
            import socketserver

            class RedirectHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(302)
                    self.send_header("Location", f"http://localhost:8501{self.path}")
                    self.end_headers()

                def log_message(self, *args):
                    pass

            try:
                with socketserver.TCPServer(("127.0.0.1", 3000), RedirectHandler) as srv:
                    srv.serve_forever()
            except Exception:
                pass

        threading.Thread(target=run_port_3000_redirect, daemon=True).start()

        import streamlit.config as cfg

        flag_options = {
            "server.headless": False,
            "server.port": 8501,
            "browser.serverPort": 8501,
            "browser.serverAddress": "localhost",
            "browser.gatherUsageStats": False,
            "global.developmentMode": False,
            "server.runOnSave": False,
        }

        bootstrap.load_config_options(flag_options)
        cfg.set_option("global.developmentMode", False)
        cfg.set_option("server.port", 8501)
        cfg.set_option("browser.serverPort", 8501)
        cfg.set_option("server.headless", False)

        bootstrap.run(target_dashboard, is_hello=False, args=[], flag_options=flag_options)
        return True
    except Exception as e:
        print(f"[DClean] Could not start Streamlit in-process: {e}")
        return False

def launch_desktop_gui(initial_file: Optional[str] = None):
    """
    Native lightweight GUI for drag-and-drop cleaning, contract selection, and audit review.
    Works with zero additional dependencies via built-in tkinter/ttk.
    """
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    root = tk.Tk()
    root.title("DClean - Data Cleaning & Entity Resolution")
    root.geometry("720x560")
    root.minsize(640, 480)

    # Set icon if available
    icon_candidates = [
        os.path.join(PROJECT_ROOT, "installer", "assets", "dclean_icon.ico"),
        os.path.join(PROJECT_ROOT, "assets", "dclean_icon.ico"),
        os.path.join(os.path.dirname(__file__), "assets", "dclean_icon.ico")
    ]
    for ic in icon_candidates:
        if os.path.exists(ic):
            try:
                root.iconbitmap(ic)
                break
            except Exception:
                pass

    # Styling
    style = ttk.Style(root)
    style.theme_use("clam")

    # Header frame
    header_frame = ttk.Frame(root, padding=15)
    header_frame.pack(fill="x")

    title_lbl = ttk.Label(
        header_frame,
        text="DClean Data Processing Studio",
        font=("Segoe UI", 16, "bold"),
        foreground="#0284c7"
    )
    title_lbl.pack(anchor="w")

    subtitle_lbl = ttk.Label(
        header_frame,
        text="Generalized ETL, Local NLP Column Classification & MDM Entity Deduplication",
        font=("Segoe UI", 9)
    )
    subtitle_lbl.pack(anchor="w", pady=(2, 0))

    ttk.Separator(root, orient="horizontal").pack(fill="x", padx=15, pady=5)

    # Main content frame
    content_frame = ttk.Frame(root, padding=15)
    content_frame.pack(fill="both", expand=True)

    # 1. File Selection
    file_var = tk.StringVar(value=initial_file or "")

    file_lbl_frame = ttk.LabelFrame(content_frame, text=" 1. Raw Input File (.xlsx, .csv) ", padding=10)
    file_lbl_frame.pack(fill="x", pady=5)

    file_entry = ttk.Entry(file_lbl_frame, textvariable=file_var, font=("Segoe UI", 10))
    file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def browse_file():
        fn = filedialog.askopenfilename(
            title="Select Raw Dataset",
            filetypes=[("Tabular Files", "*.xlsx *.xls *.csv *.xlsm"), ("All Files", "*.*")]
        )
        if fn:
            file_var.set(fn)

    browse_btn = ttk.Button(file_lbl_frame, text="Browse...", command=browse_file)
    browse_btn.pack(side="right")

    # 2. Contract Selection Mode
    contract_mode_var = tk.StringVar(value="auto")
    contract_path_var = tk.StringVar(value="")

    contract_frame = ttk.LabelFrame(content_frame, text=" 2. Schema Contract Strategy ", padding=10)
    contract_frame.pack(fill="x", pady=5)

    auto_radio = ttk.Radiobutton(
        contract_frame,
        text="Auto-Detect Schema with Local AI/NLP Classifier (Zero Hallucination, Fast)",
        variable=contract_mode_var,
        value="auto"
    )
    auto_radio.pack(anchor="w", pady=2)

    custom_radio = ttk.Radiobutton(
        contract_frame,
        text="Use Custom Declarative YAML Contract",
        variable=contract_mode_var,
        value="custom"
    )
    custom_radio.pack(anchor="w", pady=2)

    custom_file_subframe = ttk.Frame(contract_frame)
    custom_file_subframe.pack(fill="x", pady=4)

    contract_entry = ttk.Entry(custom_file_subframe, textvariable=contract_path_var, font=("Segoe UI", 9))
    contract_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def browse_contract():
        fn = filedialog.askopenfilename(
            title="Select YAML Contract",
            filetypes=[("YAML Files", "*.yaml *.yml"), ("All Files", "*.*")]
        )
        if fn:
            contract_path_var.set(fn)
            contract_mode_var.set("custom")

    contract_browse_btn = ttk.Button(custom_file_subframe, text="Browse Contract...", command=browse_contract)
    contract_browse_btn.pack(side="right")

    # 3. Log & Results area
    log_frame = ttk.LabelFrame(content_frame, text=" Execution & Audit Log ", padding=10)
    log_frame.pack(fill="both", expand=True, pady=5)

    log_text = tk.Text(log_frame, wrap="word", font=("Consolas", 9), height=8)
    log_text.pack(fill="both", expand=True)

    def log(msg: str):
        log_text.insert("end", msg + "\n")
        log_text.see("end")
        root.update_idletasks()

    # Action buttons frame
    btn_frame = ttk.Frame(root, padding=15)
    btn_frame.pack(fill="x", side="bottom")

    last_out_dir = {"path": ""}
    last_out_excel = {"path": ""}
    last_out_db = {"path": ""}

    def open_output_folder():
        if last_out_dir["path"] and os.path.exists(last_out_dir["path"]):
            os.startfile(last_out_dir["path"])
        else:
            messagebox.showinfo("DClean", "No output generated yet.")

    def open_excel():
        if last_out_excel["path"] and os.path.exists(last_out_excel["path"]):
            os.startfile(last_out_excel["path"])
        else:
            messagebox.showinfo("DClean", "Cleaned Excel file not found.")

    def run_clean_action():
        target_file = file_var.get().strip()
        if not target_file or not os.path.exists(target_file):
            messagebox.showerror("Error", "Please specify a valid input file.")
            return

        contract = None
        if contract_mode_var.get() == "custom":
            c_file = contract_path_var.get().strip()
            if not c_file or not os.path.exists(c_file):
                messagebox.showerror("Error", "Please specify a valid YAML contract file.")
                return
            contract = c_file

        log_text.delete("1.0", "end")
        log("=" * 65)
        log("Starting DClean Processing Pipeline...")
        log(f"Input:    {target_file}")
        log(f"Strategy: {'Auto-Detect (Local NLP Model)' if not contract else contract}")
        log("-" * 65)

        clean_btn.config(state="disabled")
        root.config(cursor="wait")

        try:
            from pipeline.runner import PipelineRunner

            base_dir = os.path.dirname(os.path.abspath(target_file))
            stem = os.path.splitext(os.path.basename(target_file))[0]
            out_excel = os.path.join(base_dir, f"{stem}_Cleaned.xlsx")
            out_db = os.path.join(base_dir, f"{stem}_Cleaned.db")

            runner = PipelineRunner(contract_path=contract, db_path=out_db)
            summary = runner.run(input_file_path=target_file, output_excel_path=out_excel)

            log("\n[SUCCESS] Pipeline Finished Successfully!")
            log(f"  Total Ingested:       {summary.total_rows} rows")
            log(f"  Valid Processed:      {summary.valid_rows} rows")
            log(f"  Quarantined:          {summary.quarantined_rows} ({summary.quarantine_rate_pct}%)")
            log(f"  Unique Entities:      {summary.unique_persons_resolved}")
            log(f"  Duplicates Merged:    {summary.duplicate_events_merged}")
            log(f"  Pipeline Health:      {summary.status}")
            log("-" * 65)
            log(f"Clean Excel: {out_excel}")
            log(f"Clean Database: {out_db}")

            last_out_dir["path"] = base_dir
            last_out_excel["path"] = out_excel
            last_out_db["path"] = out_db

            excel_btn.config(state="normal")
            folder_btn.config(state="normal")
            messagebox.showinfo("Complete", f"Successfully cleaned {summary.valid_rows} records!\nHealth: {summary.status}")

        except Exception as e:
            log(f"\n[ERROR] Pipeline failed: {e}")
            messagebox.showerror("Pipeline Failure", str(e))
        finally:
            clean_btn.config(state="normal")
            root.config(cursor="")

    clean_btn = ttk.Button(btn_frame, text="⚡ Clean Data Now", command=run_clean_action, style="Accent.TButton")
    clean_btn.pack(side="left", padx=5)

    excel_btn = ttk.Button(btn_frame, text="📊 Open Cleaned Excel", command=open_excel, state="disabled")
    excel_btn.pack(side="left", padx=5)

    folder_btn = ttk.Button(btn_frame, text="📁 Open Output Folder", command=open_output_folder, state="disabled")
    folder_btn.pack(side="left", padx=5)

    def open_dashboard_from_gui():
        res = launch_streamlit_direct()
        if not res:
            messagebox.showinfo("DClean", "Could not start Streamlit web studio.\nPlease ensure Python and streamlit are installed on your machine ('pip install streamlit').")

    dash_btn = ttk.Button(btn_frame, text="🌐 Web Studio", command=open_dashboard_from_gui)
    dash_btn.pack(side="left", padx=5)

    close_btn = ttk.Button(btn_frame, text="Close", command=root.destroy)
    close_btn.pack(side="right", padx=5)

    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="DClean Desktop Launcher & Headless Processor")
    parser.add_argument("file", nargs="?", default=None, help="Optional raw tabular file to clean immediately")
    parser.add_argument("--contract", "-c", default=None, help="Optional YAML contract path")
    parser.add_argument("--gui", action="store_true", help="Force open legacy desktop GUI window")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit web dashboard")

    args = parser.parse_args()

    # 1. If a file was passed as argument without --gui (e.g. from Windows Explorer context menu)
    if args.file and not args.gui:
        success = run_headless_clean(args.file, contract_path=args.contract)
        sys.exit(0 if success else 1)

    # 2. If legacy GUI explicitly forced via --gui flag
    if args.gui:
        launch_desktop_gui(initial_file=args.file)
        return

    # 3. Default interactive mode (desktop icon, Start Menu, or double-click):
    # Directly launch modern Streamlit Web Studio in default browser with silent background!
    if launch_streamlit_direct():
        return

    # 4. Fallback only if Streamlit fails
    launch_desktop_gui(initial_file=args.file)

if __name__ == "__main__":
    main()
