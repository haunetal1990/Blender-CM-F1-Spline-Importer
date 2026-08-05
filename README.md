![alt text](https://i.postimg.cc/JzcRRC9v/Screenshot-2026-08-05-083953.png "Screenshot Blender")

# Codemasters F1 Spline to Blender Importer

This plugin allows you to import AI splines (racing lines) and camera paths from Codemasters F1 games directly into Blender.

## Requisites

Before you begin, make sure you have the following software ready to use:
*   **Ego ERP Archiver**: For opening and extracting the game files.
*   **Blender**: For the 3D import.
*   **This Plugin**: Downloaded and installed in Blender.

## Instructions

### 1. Extract the Spline File
1.  Open the **Ego ERP Archiver**.
2.  Open the `_common.erp` file of the respective track from the game directory (sample: F1 22\2022_asset_groups\environment_package\tracks).
3.  Switch to the **XML Files** tab at the top.
4.  Select the files you want to export.
5.  Export the file via the menu: **Resources** -> **Export** and save it.

### 2. Import into Blender
1.  Open **Blender**.
2.  Use the installed plugin to import the previously exported files and the cams.
3.  **Folder Structure:** The imported splines can either be placed in a custom folder within Blender, or you can use the original exported folder (including subfolders).

## Compatibility
This plugin has been successfully tested with:
*   **F1 22**
*   **F1 25** (tested with 26 tracks)

## Supported Features

| Feature | Status |
|:---|:---|
| Roads/Splines | ✅ |
| Cameras | ✅ |

Dieses Plugin ermöglicht den Import von AI-Splines und Kamerapfaden aus Codemasters F1-Spielen direkt in Blender. 

## Voraussetzungen

Bevor du startest, stelle sicher, dass folgende Software einsatzbereit ist:
* **Ego ERP Archiver**: Zum Öffnen und Extrahieren der Spieldateien.
* **Blender**: Für den 3D-Import.
* **Dieses Plugin**: Heruntergeladen und in Blender installiert.

## Anleitung

### 1. Spline-Datei extrahieren
1. Öffne den **Ego ERP Archiver**.
2. Öffne die `_common.erp`-Datei der jeweiligen Rennstrecke aus dem Spielverzeichnis (Beispiel: F1 22\2022_asset_groups\environment_package\tracks).
3. Wechsle ganz oben zum Reiter **XML Files**.
4. Wähle die Datei/en aus, die du exportieren möchtest.
5. Exportiere die Datei über das Menü: **Resources** -> **Export** und speichere sie ab.

### 2. In Blender importieren
1. Öffne **Blender**.
2. Nutze das installierte Plugin, um die zuvor exportierten Dateien sowie die Cams zu importieren.
3. **Ordnerstruktur:** Die importierten Splines können dabei in einem eigenen Ordner in Blender abgelegt werden, oder es wird der original exportierte Ordner (inklusive Unterordner) genutzt.

## Kompatibilität
Das Plugin wurde erfolgreich getestet mit:
* **F1 22**
* **F1 25** (getestet mit 26 Strecken)

## Unterstützte Importe

| Feature | Status |
|---|---|
| Straßen | ✅ |
| Kameras | ✅ |
