# 🚀 Nusantara Download Manager (NDM)

**Nusantara Download Manager (NDM)** is a modern, modular, and multi-threaded download manager built with Python. It features a sleek, responsive UI and a robust engine optimized for high-speed downloads, local database persistence, and browser integration.

![NDM Logo](ndm_logo.png)

## ✨ Key Features

- **🚀 High-Speed Engine**: Multi-threaded download architecture for maximum throughput.
- **🎨 Modern UI/UX**: Built with `CustomTkinter` featuring a dark-themed, premium aesthetic with **SemiBold Poppins** typography.
- **🌐 Localization (i18n)**: Full support for **English** and **Indonesian**, with real-time language switching.
- **🔌 Browser Integration**: Includes a dedicated Chrome Extension with a local server for seamless link capturing.
- **📊 Real-time Monitoring**: Integrated network connectivity status and detailed download progress (speed, ETA, size).
- **📂 Smart Categorization**: Automatically filters downloads into Categories (Compressed, Video, Audio, Image, etc.).
- **💾 Persistent Storage**: Uses SQLite to ensure your download history and settings are saved even after restart.
- **📥 Drag & Drop**: Easy-to-use interface for adding URLs and installing browser extensions.

## 🛠️ Technology Stack

- **Core**: Python 3.x
- **GUI**: CustomTkinter / Tkinter (with Pillow for imaging)
- **Database**: SQLite3
- **Styling**: Vanilla CSS (Extensions) & Custom Poppins Typography
- **System**: Pystray (System Tray Integration)

## 🚀 Getting Started

### Prerequisites

Ensure you have Python 3.10+ installed. Install the required dependencies:

```bash
pip install customtkinter pillow pystray requests
```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/posann/NDM.git
   cd NDM
   ```
2. Run the application:
   ```bash
   python app.py
   ```

## 📁 Project Structure

```text
├── core/               # Download logic, server, and manager
├── ui/                 # UI pages, components, and main window
├── utils/              # Database, localization, and helper utilities
├── localization/       # Language JSON files (en.json, id.json)
├── fonts/              # Custom Poppins TTF files
├── extension/          # Chrome Extension source code
└── app.py              # Application entry point
```

## 📜 License

This project is maintained by **posann**. All rights reserved.

---

_Crafted with ❤️ in Nusantara._
