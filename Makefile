PREFIX ?= /usr
BIN_DIR = $(PREFIX)/bin
DESKTOP_DIR = $(PREFIX)/share/applications
ICON_DIR = $(PREFIX)/share/icons/hicolor/48x48/apps
DOC_DIR = $(PREFIX)/share/licenses/llama.cpp-server-tray

install: install_bin install_desktop install_icons install_docs

install_bin:
	install -Dm755 llama.cpp-server-tray $(DESTDIR)$(BIN_DIR)/llama.cpp-server-tray

install_desktop:
	install -Dm755 llama.cpp-server-tray.desktop $(DESTDIR)$(DESKTOP_DIR)/llama.cpp-server-tray.desktop

install_icons:
	install -Dm644 llama_service_running.png $(DESTDIR)$(ICON_DIR)/llama_service_running.png
	install -Dm644 llama_service.png $(DESTDIR)$(ICON_DIR)/llama_service.png

install_docs:
	install -Dm644 README.md $(DESTDIR)$(DOC_DIR)/README.md
	install -Dm644 LICENSE $(DESTDIR)$(DOC_DIR)/LICENSE

uninstall:
	rm -f $(DESTDIR)$(BIN_DIR)/llama.cpp-server-tray
	rm -f $(DESTDIR)$(DESKTOP_DIR)/llama.cpp-server-tray.desktop
	rm -f $(DESTDIR)$(ICON_DIR)/llama_service_running.png
	rm -f $(DESTDIR)$(ICON_DIR)/llama_service.png
	rm -rf $(DESTDIR)$(DOC_DIR)

.PHONY: install install_bin install_desktop install_icons install_docs uninstall
