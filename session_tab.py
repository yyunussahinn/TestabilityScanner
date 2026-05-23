"""
session_tab.py — Where is My Id  v1.1
────────────────────────────────────────────────────────────────
Multi-page session tarama mantığı.

v1.1: Akış bazlı toplama
  - Oturum açılırken bir kere akış adı girilir (örn: "loyalty")
  - Her "Sayfayı Topla" işlemi otomatik numaralanır:
      loyalty - tarama 1, loyalty - tarama 2, ...
  - Tablo'da her tarama ayrı satır gösterilir
  - Excel/Word'e yazarken hepsi tek sheet/dosya altında toplanır (flow_name)
"""

import threading
import os
from datetime import datetime
from collections import Counter


class SessionTab:

    def __init__(self, app_ref):
        self.app = app_ref

        self._driver         = None
        self._platform       = "ios"
        self._pixel_ratio    = 1.0
        self._running        = False
        self._collecting     = False

        # Akış bilgisi
        self._flow_name      = ""   # kullanıcının girdiği akış adı (örn: "loyalty")
        self._scan_counter   = 0    # kaçıncı tarama (1'den başlar)

        # Biriken veriler
        # element'lerin "page" field'ı → "loyalty - tarama 1" gibi etiket taşır
        # ama Excel sheet adı her zaman self._flow_name olur
        self._all_elements:  list[dict] = []
        self._page_summary:  list[dict] = []  # [{label, unique, undefined, duplicate, missing, total, ss_path}]

        # Bağlanan widget'lar (app.py set eder)
        self._log_box         = None
        self._update_table_cb = None

    # ── Bağlama ──────────────────────────────────────────────────────────────
    def bind_log(self, log_box):
        self._log_box = log_box

    def bind_table_callback(self, cb):
        self._update_table_cb = cb

    # ── Log ──────────────────────────────────────────────────────────────────
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

    # ── Oturumu Başlat ────────────────────────────────────────────────────────
    def start_session(self, flow_name: str):
        """Footer 'OTURUMU BAŞLAT' butonundan flow_name ile çağrılır."""
        if self._driver:
            self._log("⚠️  Zaten aktif bir oturum var. Önce 'Bitti' ile kapatın.", "warn")
            return

        if not flow_name.strip():
            self._log("❌ Akış adı boş olamaz!", "err")
            return

        pf = self.app.v_platform.get()
        if pf == "ios":
            profile = self.app.ios_panel.get_data()
            if not profile.get("bundle_id"):
                self._log("❌ iOS Bundle ID boş!", "err")
                return
        else:
            profile = self.app.and_panel.get_data()
            if not profile.get("app_package"):
                self._log("❌ Android App Package boş!", "err")
                return

        output_dir = self.app.v_out_dir.get().strip()
        if not output_dir:
            self._log("❌ Çıktı klasörü boş!", "err")
            return

        # State sıfırla
        self._flow_name    = flow_name.strip()
        self._scan_counter = 0
        self._all_elements.clear()
        self._page_summary.clear()
        if self._update_table_cb:
            self.app.after(0, self._update_table_cb)

        self._platform = pf
        self._running  = True
        self.app.after(0, lambda: self.app._set_session_state("connected"))

        self._log(f"{'='*50}", "dim")
        self._log(f"🔌 Oturum başlatılıyor... ({pf.upper()})", "info")
        self._log(f"   Akış adı: {self._flow_name}", "info")

        threading.Thread(
            target=self._connect_worker,
            args=(pf, profile, self.app.v_appium.get()),
            daemon=True
        ).start()

    def _connect_worker(self, platform, profile, appium_server):
        try:
            from appium import webdriver

            if platform == "ios":
                from appium.options.ios import XCUITestOptions
                options = XCUITestOptions()
                options.platform_name    = "iOS"
                options.device_name      = profile["device_name"]
                options.platform_version = profile["platform_version"]
                options.automation_name  = "XCUITest"
                options.bundle_id        = profile["bundle_id"]
                options.no_reset         = profile.get("no_reset", True)
                options.udid             = profile["udid"]
            else:
                from appium.options.android import UiAutomator2Options
                options = UiAutomator2Options()
                options.platform_name    = "Android"
                options.device_name      = profile["device_name"]
                options.platform_version = profile["platform_version"]
                options.automation_name  = "UiAutomator2"
                options.app_package      = profile["app_package"]
                options.app_activity     = profile["app_activity"]
                options.no_reset         = profile.get("no_reset", True)

            self._driver = webdriver.Remote(appium_server, options=options)

            # iOS pixel ratio
            if platform == "ios":
                try:
                    import tempfile, os as _os
                    tmp = tempfile.mktemp(suffix=".png")
                    self._driver.get_screenshot_as_file(tmp)
                    from PIL import Image as PILImage
                    with PILImage.open(tmp) as img:
                        ss_w, _ = img.size
                    _os.remove(tmp)
                    win = self._driver.get_window_size()
                    pt_w = win.get("width", ss_w)
                    self._pixel_ratio = ss_w / pt_w if pt_w > 0 else 1.0
                    self._log(f"   pixel_ratio: {self._pixel_ratio:.1f}x", "dim")
                except Exception:
                    self._pixel_ratio = 1.0
            else:
                self._pixel_ratio = 1.0

            self._log("✅ Appium bağlandı!", "ok")
            self._log(f"   → Uygulamada ilk sayfayı açın ve 'Sayfayı Topla'ya basın.", "dim")
            self._log(f"   → Her sayfadan sonra tekrar 'Sayfayı Topla'ya basın.", "dim")
            self._log(f"   → Bitince 'Bitti - Rapor Oluştur'a basın.", "dim")

        except Exception as ex:
            self._log(f"❌ Bağlantı hatası: {ex}", "err")
            self._driver  = None
            self._running = False
            self.app.after(0, lambda: self.app._set_session_state("idle"))

    # ── Sayfayı Topla ─────────────────────────────────────────────────────────
    def collect_page(self):
        """'Sayfayı Topla' butonundan çağrılır. Akış adı zaten set edilmiş."""
        if not self._driver:
            self._log("❌ Önce 'Oturumu Başlat' ile Appium'a bağlanın.", "err")
            return
        if self._collecting:
            self._log("⏳ Zaten toplama işlemi devam ediyor, bekleyin.", "warn")
            return

        self._scan_counter += 1
        # Tablo etiketi: "loyalty - tarama 1"
        scan_label = f"{self._flow_name} - tarama {self._scan_counter}"

        self._collecting = True
        self.app.after(0, lambda: self.app._set_session_state("collecting"))
        self._log(f"─── {scan_label} ─── element taranıyor...", "info")

        threading.Thread(
            target=self._collect_worker,
            args=(scan_label,),
            daemon=True
        ).start()

    def _collect_worker(self, scan_label: str):
        try:
            import smart_checker as sc

            output_dir = self.app.v_out_dir.get().strip()
            ss_dir     = os.path.join(output_dir, f"screenshots_{self._platform}")
            os.makedirs(ss_dir, exist_ok=True)
            ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Screenshot dosya adında scan_label'i temizle (dosya adı uyumlu)
            safe_label = scan_label.replace(" ", "_").replace("-", "").replace("/", "_")
            ss_path    = os.path.join(ss_dir, f"{safe_label}_{ts}.png")
            self._driver.get_screenshot_as_file(ss_path)

            win = self._driver.get_window_size()
            sw, sh = win["width"], win["height"]

            elements = sc._collect_elements(
                self._driver, self._platform,
                scan_label,   # element'lerin "page" field'ı bu etiketi taşır
                sw, sh, self._pixel_ratio,
                self._log
            )

            # page field'ı scan_label (tablo görünümü için)
            for e in elements:
                e["page"]      = scan_label
                e["flow_name"] = self._flow_name   # Excel sheet adı için

            # AI Suggestion
            import shared as shr
            elements = shr.enrich_with_ai(elements, self._platform)

            self._all_elements.extend(elements)

            counts = Counter(e["status"] for e in elements)
            summary = {
                "label":     scan_label,        # tablo satır etiketi
                "flow":      self._flow_name,   # Excel sheet adı
                "unique":    counts["ID Var"],
                "undefined": counts["Undefined ID"],
                "duplicate": counts["Duplicate"],
                "missing":   counts["ID Yok"],
                "total":     len(elements),
                "ss_path":   ss_path,
            }
            self._page_summary.append(summary)

            self._log(
                f"✅ {scan_label}: "
                f"✓{summary['unique']} "
                f"⚠{summary['undefined']} "
                f"🔁{summary['duplicate']} "
                f"✗{summary['missing']} "
                f"(toplam {summary['total']})",
                "ok"
            )

            if self._update_table_cb:
                self.app.after(0, self._update_table_cb)

            self.app.after(0, lambda: self.app._set_session_state("connected"))

        except Exception as ex:
            import traceback
            self._log(f"❌ Toplama hatası: {ex}", "err")
            self._log(traceback.format_exc(), "err")
            # Sayacı geri al (başarısız tarama numarayı yakmamalı)
            self._scan_counter -= 1
            self.app.after(0, lambda: self.app._set_session_state("connected"))
        finally:
            self._collecting = False

    # ── Bitti - Rapor Oluştur ─────────────────────────────────────────────────
    def finish_session(self):
        if not self._all_elements:
            self._log("⚠️  Hiç element toplanmadı. Önce 'Sayfayı Topla' kullanın.", "warn")
            return

        self.app.after(0, lambda: self.app._set_session_state("finishing"))
        total_scans = len(self._page_summary)
        self._log(f"{'='*50}", "dim")
        self._log(
            f"📊 Rapor oluşturuluyor... "
            f"({len(self._all_elements)} element, {total_scans} tarama, akış: {self._flow_name})",
            "info"
        )

        threading.Thread(target=self._finish_worker, daemon=True).start()

    def _finish_worker(self):
        try:
            if self._driver:
                try:
                    self._driver.quit()
                    self._log("🔌 Driver kapatıldı.", "dim")
                except Exception:
                    pass
                self._driver = None

            import shared as shr

            output_dir   = self.app.v_out_dir.get().strip()
            cfg          = self.app._collect()
            fmt_parts    = set()
            if cfg.get("output_word"):  fmt_parts.add("word")
            if cfg.get("output_excel"): fmt_parts.add("excel")
            if cfg.get("output_json"):  fmt_parts.add("json")

            doc_sections = cfg.get("document_sections",
                                   ["unique", "undefined", "duplicate", "missing"])
            plat_suffix  = "IOS" if self._platform == "ios" else "Android"
            ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
            flow_safe    = self._flow_name.replace(" ", "_")

            # EXCEL — var olan dosyaya yeni sheet ekle (yoksa yeni dosya oluştur)
            if "excel" in fmt_parts:
                excel_file = os.path.join(
                    output_dir, f"Session_{flow_safe}_{plat_suffix}.xlsx")

                # Oturum numarasını belirle: dosyada kaç "{flow_name}" içeren sheet varsa +1
                import openpyxl as _opxl
                if os.path.exists(excel_file):
                    _wb_check = _opxl.load_workbook(excel_file, read_only=True)
                    existing  = [s for s in _wb_check.sheetnames
                                 if s.startswith(self._flow_name)]
                    _wb_check.close()
                    session_num = len(existing) + 1
                else:
                    session_num = 1

                sheet_name = (self._flow_name if session_num == 1
                              else f"{self._flow_name} - oturum {session_num}")

                self._log(f"   Sheet adı: '{sheet_name}'", "dim")

                STATUS_ORDER = {
                    "ID Var":       0,
                    "Undefined ID": 1,
                    "Duplicate":    2,
                    "ID Yok":       3,
                }

                first_scan = True
                for s in self._page_summary:
                    scan_elems = [e for e in self._all_elements
                                  if e.get("page") == s["label"]]
                    scan_elems.sort(
                        key=lambda e: STATUS_ORDER.get(e.get("status", ""), 99))

                    if first_scan:
                        # İlk tarama: sheet'i generate_excel ile oluştur
                        # (dosya yoksa yeni dosya, varsa mevcut dosyaya yeni sheet)
                        shr.generate_excel(
                            all_elements=scan_elems,
                            page_name=sheet_name,
                            excel_file=excel_file,
                            document_sections=doc_sections,
                            platform=self._platform,
                            screenshot_path="",
                        )
                        first_scan = False
                    else:
                        # Sonraki taramalar: aynı sheet'e satır ekle
                        self._append_scan_rows(
                            excel_file, sheet_name, scan_elems,
                            doc_sections, shr)

                # Tüm tarama screenshotlarını Excel'e alt alta ekle
                self._append_screenshots_to_excel(excel_file, sheet_name)
                self._log(f"📊 Excel kaydedildi: {excel_file}  (sheet: {sheet_name})", "ok")

            # WORD — her tarama ayrı dosya
            if "word" in fmt_parts:
                for s in self._page_summary:
                    scan_elems  = [e for e in self._all_elements if e.get("page") == s["label"]]
                    safe_lbl    = s["label"].replace(" ", "_").replace("-", "").replace("/", "_")
                    word_file   = os.path.join(
                        output_dir, f"{safe_lbl}_{plat_suffix}.docx")
                    shr.generate_word(
                        all_elements=scan_elems,
                        page_name=s["label"],
                        word_file=word_file,
                        document_sections=doc_sections,
                        platform=self._platform,
                        screenshot_path=s.get("ss_path", ""),
                    )
                    self._log(f"📄 Word: {os.path.basename(word_file)}", "ok")

            # JSON — tüm unique elementler tek dosya
            if "json" in fmt_parts:
                json_file = os.path.join(
                    output_dir, f"Session_{flow_safe}_{self._platform}_{ts}.json")
                shr.generate_json(
                    elements=self._all_elements,
                    page_name=self._flow_name,
                    json_file=json_file,
                    platform=self._platform,
                )

            self._log(f"{'='*50}", "dim")
            self._log(
                f"✅ Tamamlandı! Akış: {self._flow_name}  |  "
                f"{len(self._page_summary)} tarama  |  "
                f"{len(self._all_elements)} element",
                "ok"
            )
            self.app.after(0, lambda: self.app.badge.set("ok"))

        except Exception as ex:
            import traceback
            self._log(f"❌ Rapor hatası: {ex}", "err")
            self._log(traceback.format_exc(), "err")
            self.app.after(0, lambda: self.app.badge.set("error"))
        finally:
            self._running    = False
            self._collecting = False
            self.app.after(0, lambda: self.app._set_session_state("idle"))

    # ── Sonraki tarama satırlarını mevcut sheet'e ekle ───────────────────────
    def _append_scan_rows(self, excel_file, sheet_name, scan_elems, doc_sections, shr):
        """
        İlk tarama generate_excel ile yazıldı. Sonraki taramaların elementlerini
        mevcut sheet'in sonuna ekler — başlık satırı yazmadan.
        Stil için shared.py'deki yardımcı fonksiyonları kullanır.
        """
        import openpyxl
        from openpyxl.styles import Font, Alignment
        from openpyxl.utils import get_column_letter

        wb  = openpyxl.load_workbook(excel_file)
        ws  = wb[sheet_name]

        # Mevcut son satırı bul
        last_row = ws.max_row + 1

        # Elementleri sıralı yaz
        ordered = shr._build_ordered(scan_elems, doc_sections)
        # _build_ordered zaten status sırasına göre grupluyor — ama scan_elems
        # tek bir taramaya ait olduğu için gruplar tarama içinde kalır. ✓

        # Mevcut satır sayısından element index başlat (numaralama için)
        # idx için sayfadaki veri satır sayısını hesapla (başlık 2 satır)
        data_rows_so_far = last_row - 3  # 2 başlık + 1 offset
        if data_rows_so_far < 0:
            data_rows_so_far = 0

        plat = self._platform
        acc_col  = "Accessibility ID" if plat == "ios" else "Resource ID"
        COL_KEYS = ["element_id", "page", "type", "label", "value",
                    "acc_id", "status", "new_status", "ai_suggestion"]

        for idx, elem in enumerate(ordered):
            elem_id    = f"{sheet_name}_element_{data_rows_so_far + idx + 1}"
            status     = elem.get("status", "ID Yok")
            new_status = shr.get_new_status(status)
            row_num    = last_row + idx
            pal        = shr.STATUS_PALETTE.get(status, shr.STATUS_PALETTE["ID Yok"])
            r_fill     = shr.fill(pal["row"] if idx % 2 == 0 else pal["alt"])
            ns_fill    = shr.fill(shr.NEW_STATUS_COLOR["row"] if idx % 2 == 0
                                  else shr.NEW_STATUS_COLOR["alt"])
            ai_fill    = shr.fill(shr.AI_SUGGESTION_COLOR["row"] if idx % 2 == 0
                                  else shr.AI_SUGGESTION_COLOR["alt"])

            for ci, key in enumerate(COL_KEYS, 1):
                val = shr._get_val(elem, key, elem_id, new_status)
                c   = ws.cell(row=row_num, column=ci, value=val)
                c.border = shr.BORDER
                shr._style_excel_cell(c, key, pal, r_fill, ns_fill, ai_fill, new_status)

            ws.row_dimensions[row_num].height = 60

        shr.safe_save(wb, excel_file)

    # ── Screenshotları Excel'e ekle ───────────────────────────────────────────
    def _append_screenshots_to_excel(self, excel_file: str, sheet_name: str):
        """
        self._page_summary içindeki tüm ss_path'leri,
        mevcut sheet'teki veri sütunlarının sağına alt alta ekler.
        Her screenshot üstünde "📸 loyalty - tarama N" etiketi olur.
        Aralarında 2 satır boşluk bırakır.
        """
        try:
            import openpyxl
            from openpyxl.drawing.image import Image as XLImage
            from PIL import Image as PILImage
            import shared as shr

            wb = openpyxl.load_workbook(excel_file)
            if sheet_name not in wb.sheetnames:
                self._log(f"⚠️  Sheet '{sheet_name}' bulunamadı, screenshot eklenemedi.", "warn")
                return
            ws = wb[sheet_name]

            data_cols   = ws.max_column
            img_col_idx = data_cols + 2
            from openpyxl.utils import get_column_letter
            img_col_ltr = get_column_letter(img_col_idx)

            ws.column_dimensions[get_column_letter(data_cols + 1)].width = 2
            ws.column_dimensions[img_col_ltr].width = 44

            current_row = 1
            tmp_files   = []

            for s in self._page_summary:
                ss_path = s.get("ss_path", "")
                label   = s.get("label", "tarama")

                if not ss_path or not os.path.exists(ss_path):
                    continue

                try:
                    with PILImage.open(ss_path) as img:
                        orig_w, orig_h = img.size
                    target_w = 300
                    target_h = int(orig_h * target_w / orig_w)

                    tmp_path = ss_path.replace(".png", "_xl_tmp.png")
                    with PILImage.open(ss_path) as img:
                        img.resize((target_w, target_h), PILImage.LANCZOS).save(tmp_path, "PNG")
                    tmp_files.append(tmp_path)

                    # Etiket hücresi
                    label_cell = ws.cell(row=current_row, column=img_col_idx,
                                         value=f"📸 {label}")
                    label_cell.font      = openpyxl.styles.Font(bold=True, color="1F4E79", size=10)
                    label_cell.fill      = openpyxl.styles.PatternFill("solid", fgColor="DEEAF1")
                    label_cell.alignment = openpyxl.styles.Alignment(
                        horizontal="center", vertical="center")
                    ws.row_dimensions[current_row].height = 20
                    current_row += 1

                    # Resmi ekle
                    xl_img        = XLImage(tmp_path)
                    xl_img.width  = target_w
                    xl_img.height = target_h
                    ws.add_image(xl_img, f"{img_col_ltr}{current_row}")

                    # Resmin kapladığı satır sayısı — Excel'de 1 satır ≈ 15px
                    rows_needed = max(1, target_h // 15 + 1)
                    for r in range(current_row, current_row + rows_needed):
                        ws.row_dimensions[r].height = 15
                    current_row += rows_needed

                    # Resimler arası 2 satır boşluk
                    ws.row_dimensions[current_row].height = 8
                    ws.row_dimensions[current_row + 1].height = 8
                    current_row += 2

                except Exception as e:
                    self._log(f"⚠️  {label} screenshot eklenemedi: {e}", "warn")

            shr.safe_save(wb, excel_file)

            for tmp in tmp_files:
                try:
                    os.remove(tmp)
                except OSError:
                    pass

            self._log(f"   📸 {len(self._page_summary)} screenshot Excel'e eklendi.", "dim")

        except Exception as ex:
            self._log(f"⚠️  Screenshot ekleme hatası: {ex}", "warn")

    # ── Oturumu iptal et ──────────────────────────────────────────────────────
    def abort_session(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
        self._running    = False
        self._collecting = False
        self._log("■ Oturum durduruldu.", "warn")
        self.app.after(0, lambda: self.app._set_session_state("idle"))

    # ── Yardımcılar ───────────────────────────────────────────────────────────
    @property
    def is_active(self):
        return self._driver is not None

    @property
    def scan_count(self):
        return self._scan_counter

    @property
    def flow_name(self):
        return self._flow_name

    @property
    def summary(self):
        return list(self._page_summary)