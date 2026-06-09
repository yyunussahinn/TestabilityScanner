"""
smart_tab.py — v4.2  (i18n)
────────────────────────────────────────────────────────────────
Smart Tarama mantık sınıfı.
Tüm log ve hata mesajları i18n.t() üzerinden yönetilir.
"""

import threading
import os
from datetime import datetime
from i18n import t


class SmartTab:

    def __init__(self, app_ref):
        self.app = app_ref
        self._running         = False
        self._all_elements    = []
        self._screenshot_path = ""
        self._detected_page   = ""
        self._boxes           = []

        self._log_box    = None
        self._page_frame = None
        self._page_var   = None
        self._submit_cb  = None

    def bind_to_log(self, log_box):
        self._log_box = log_box

    def bind_page_frame(self, frame, var, submit_cb):
        self._page_frame = frame
        self._page_var   = var
        self._submit_cb  = submit_cb

    def _log(self, text, tag=""):
        if not self._log_box:
            return
        def _d():
            self._log_box.configure(state="normal")
            ts = datetime.now().strftime("%H:%M:%S")
            self._log_box._textbox.insert("end", f"[{ts}] {text}\n", tag or "")
            self._log_box._textbox.see("end")
            self._log_box.configure(state="disabled")
        self.app.after(0, _d)

    def run_connect_from_footer(self):
        self._run_connect()

    def submit_page(self, page_name: str):
        if not page_name:
            self._log(t("smart_log_page_empty"), "warn")
            return
        if self._page_frame:
            self.app.after(0, self._page_frame.grid_remove)
        self._log(f"📄 {t('lbl_page_name')} {page_name}", "info")
        self._log(t("smart_log_report_gen"), "info")
        threading.Thread(
            target=self._report_worker,
            args=(page_name,),
            daemon=True).start()

    def stop(self):
        self._running = False
        self.app.after(0, lambda: self.app._set_busy(False))
        self._log(t("smart_log_stopped"), "warn")

    def _run_connect(self):
        pf = self.app.v_platform.get()
        if pf == "ios":
            profile = self.app.ios_panel.get_data()
            if not profile.get("bundle_id"):
                self._log(t("smart_log_ios_bundle_empty"), "err")
                return
        else:
            profile = self.app.and_panel.get_data()
            if not profile.get("app_package"):
                self._log(t("smart_log_and_pkg_empty"), "err")
                return

        output_dir = self.app.v_out_dir.get().strip()
        if not output_dir:
            self._log(t("smart_log_output_empty"), "err")
            return

        if self._log_box:
            self.app.after(0, lambda: (
                self._log_box.configure(state="normal"),
                self._log_box.delete("1.0", "end"),
                self._log_box.configure(state="disabled")
            ))

        self.app.after(0, lambda: self.app._set_busy(True))
        self._log(t("smart_log_connecting", platform=pf.upper()), "info")
        self._log("-" * 50, "dim")

        ss_dir  = os.path.join(output_dir, f"screenshots_{pf}")
        os.makedirs(ss_dir, exist_ok=True)
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        ss_path = os.path.join(ss_dir, f"smart_{ts}.png")

        self._running = True
        threading.Thread(
            target=self._connect_worker,
            args=(pf, profile, self.app.v_appium.get(), ss_path),
            daemon=True).start()

    def _connect_worker(self, platform, profile, appium_server, ss_path):
        try:
            from smart_checker import connect_and_capture

            elements, detected_page = connect_and_capture(
                platform=platform,
                profile=profile,
                appium_server=appium_server,
                screenshot_path=ss_path,
                log_cb=self._log,
            )

            self._all_elements    = elements
            self._screenshot_path = ss_path
            self._detected_page   = detected_page

            self._log("", "")
            self._log(t("smart_log_screenshot_ready"), "ok")

            self.app.after(300, lambda: self._open_annotation(ss_path))

        except Exception as ex:
            self._log(t("smart_log_error", error=ex), "err")
            self.app.after(0, lambda: self.app._set_busy(False))

    def _open_annotation(self, ss_path):
        from annotator import open_annotator

        self._log(t("smart_log_annotate_hint"), "warn")

        root  = self.app
        boxes = open_annotator(root, ss_path)

        if not boxes:
            self._log(t("smart_log_annotation_cancel"), "warn")
            self.app.after(0, lambda: self.app._set_busy(False))
            return

        self._boxes = boxes
        self._log(t("smart_log_boxes_marked", n=len(boxes)), "ok")

        if self._page_var:
            self._page_var.set("")
        if self._page_frame:
            self.app.after(0, lambda: self._page_frame.grid(row=2, column=0, sticky="ew"))

    def _report_worker(self, page_name: str):
        try:
            from claude_filter import filter_elements_by_boxes
            from smart_checker import generate_reports

            pf         = self.app.v_platform.get()
            output_dir = self.app.v_out_dir.get().strip()

            cfg = self.app._collect()
            output_fmt = self._build_fmt(cfg)
            document_sections = cfg.get("document_sections",
                                         ["unique", "undefined", "duplicate", "missing"])

            use_vision = bool(
                os.environ.get("ANTHROPIC_API_KEY", "").strip()
                or os.path.exists(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), ".anthropic_key"))
            )

            if not use_vision:
                self._log(t("smart_log_no_api_key"), "warn")

            filtered = filter_elements_by_boxes(
                all_elements=self._all_elements,
                boxes=self._boxes,
                screenshot_path=self._screenshot_path,
                use_vision=use_vision,
            )

            self._log(t("smart_log_elements_count", n=len(filtered)), "info")

            import shared as sh
            filtered = sh.enrich_with_ai(filtered, pf)

            self._log(t("smart_log_report_gen"), "info")

            generate_reports(
                elements=filtered,
                page_name=page_name,
                output_dir=output_dir,
                platform=pf,
                screenshot_path=self._screenshot_path,
                output_fmt=output_fmt,
                document_sections=document_sections,
                log_cb=self._log,
            )

            self._log("-" * 50, "dim")
            self._log(t("smart_log_done"), "ok")
            self.app.after(0, lambda: self.app.badge.set("ok"))

        except Exception as ex:
            import traceback
            self._log(t("smart_log_error", error=ex), "err")
            self._log(traceback.format_exc(), "err")
            self.app.after(0, lambda: self.app.badge.set("error"))
        finally:
            self.app.after(0, lambda: self.app._set_busy(False))

    @staticmethod
    def _build_fmt(cfg) -> str:
        parts = []
        if cfg.get("output_word"):  parts.append("word")
        if cfg.get("output_excel"): parts.append("excel")
        if cfg.get("output_json"):  parts.append("json")
        return "+".join(parts) if parts else "word"