# WHERE IS MY ID — config.py  (17.06.2026 10:55)
PLATFORM = "android"
BLACKLIST_IDS = ["LinearLayout", "FrameLayout", "text-input-flat-label-inactive", "text-input-underline", "right-icon-adornment-container", "right-icon-adornment", "text-input-flat", "statusBarBackground", "content", "action_bar_root", "navigationBarBackground", "exo_content_frame"]
OUTPUT_FORMAT = "excel+json"
DOCUMENT_SECTIONS = ["unique", "undefined", "duplicate", "missing"]
OUTPUT_DIR = "/Users/yunus.sahin/Library/CloudStorage/OneDrive-TESTINIUMTeknolojiYazılımA.Ş/Demo/Tam Tarama"
APPIUM_SERVER = "http://127.0.0.1:4723"
ANDROID = {
    "device_name":      "ce04171418dee0010c",
    "platform_version": "9",
    "app_package":      "com.booking",
    "app_activity":     "com.booking/.startup.HomeActivity",
    "no_reset":         True,
}
IOS = {}
