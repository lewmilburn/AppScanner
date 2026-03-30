# AppScanner

AppScanner is a security testing tool that downloads, decompiles, and scans Android applications. Once scanned, the
script then generates a JSON report that can be used into other tools and a HTML report that can be opened in your
browser and shared with others.

The JSON report contains raw and redacted credentials (if any are found), the HTML report only contains redacted 
credentials.

## Requirements & Setup
AppScanner supports Windows (10 build 1511 or newer), Linux, and macOS devices running on amd64 or arm64 processors. However, we have not tested 
the tool on Linux or macOS.

AppScanner requires cURL to work, it is bundled with most operating systems, but may need installing if you don't 
already have it.

If you download a lot of apps, a lot of disk space will be used.

Windows: If it does not run in PowerShell, try the standard command prompt.

## Usage
To use AppScanner, simply run `py AppScanner.py -a=[appID]`

The App ID is the package name. For example: `com.bbc.sounds`, you can get these from the URL bar on Google Play.

**You MUST pass ONE of the following arguments:**

| Long               | Short | Example                                | Description                                                                                 |
|--------------------|-------|----------------------------------------|---------------------------------------------------------------------------------------------|
| `--app`            | `-a`  | `py AppScanner.py -a=com.bbc.sounds`   | Downloads an APK package.                                                                   |
| `--search`         | `-q`  | `py AppScanner.py -q="BBC Sounds"`     | Searches for APK packages.                                                                  |
| `--categoryList`   | `-cl` | `py AppScanner.py -cl`                 | Gets a list of all available APK categories, then allows you to search one.                 |
| `--categorySearch` | `-cs` | `py AppScanner.py -cs="entertainment"` | Search APKPure for apps in a specific category.                                             |
| `--list=FILENAME`  | `-l`  | `py AppScanner.py -l`                  | Pass in a file containing a list of App IDs to be downloaded, see "Bulk Downloading" below. |
| `--skip-dl`        | `-s`  | `py AppScanner.py -s`                  | Skips the download/search step, only scanning files already in the "apps" directory.        |

**You may also pass one of the following arguments if required:**

| Long          | Short | Example                                 | Description                                                                                                                                                                                                                                                         |
|---------------|-------|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--keep`      | `-k`  | `py AppScanner.py -a=com.bbc.sounds -k` | After scanning AppScanner automatically deletes APKs to free up disk space, passing this argument stops them from being deleted. This may result in considerably higher disk usage.                                                                                 |
| `--save-list` | `-k`  | `py AppScanner.py -cl --save-list`      | Instead of downloading the apps right away, AppScanner will create a wordlist. This allows you to select apps from multiple categories and then pass the list in using the --list flag instead. If file exists, it will ask you if you want to overwrite or append. |

### Bulk Downloading
To download multiple apps at once, create a file (for example name it apps.txt) and put an App ID on each line.

Next, run `py AppScanner.py --list=apps.txt` and AppScanner will begin to process the apps.

If you are scanning pre-downloaded files you don't need to include a list file.

Alternatively, you can search for files using `py AppScanner.py --search=[Search Term]` and bulk-download all returned
results.

### Scanning pre-downloaded apps
If you already have apps downloaded, create a folder named "apps" within the AppScanner directory and put your apps in 
there.

Next, run `py AppScanner.py -s`, passing the `-s` argument to `AppScanner.py`. This will skip the download step and 
begin scanning all files in the apps folder.

### Supported App Types
AppScanner supports Android apps, including those in `.apk`, `.apkm`, `.xapk`, and `.apks` formats.

## Troubleshooting
### APKTool
- This version of AppScanner is bundled with APKTool 3.0.1, if you update it ensure the filenames match.
- APKTool requires Java.

### Trufflehog
- This version of AppScanner is bundled with Trufflehod 3.93.6, if you update it delete all of the Trufflehog binaries, delete installed.conf, and drop the new .tar.gz files in the libs folder, do not rename them.
- Checksums for the binaries are available at https://github.com/trufflesecurity/trufflehog/releases/tag/v3.93.6
- Not running? Try `chmod +x /libs/trufflehog_[OS]` if on Linux/macOS.
- Trufflehog is distributed with AppScanner and will be extracted automatically on first run.

## Roadmap
- App ID searching