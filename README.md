# AppScanner

_Created by Lewis Milburn at KPMG UK - lewis.milburn@kpmg.co.uk_

AppScanner is a security testing tool that downloads, decompiles, and scans Android applications. Once scanned, the
script then generates a JSON report that can be used into other tools and a HTML report that can be opened in your
browser and shared with others.

The JSON report contains raw and redacted credentials (if any are found), the HTML report only contains redacted 
credentials.

> ⚠️ **./libs/gplaycli.conf contains YOUR Google account credentials, DO NOT share it with anyone!**
> Make sure to double-check it is empty if you are sharing AppScanner with anyone!

## Requirements & Setup
AppScanner supports Windows, Linux, and macOS devices running on amd64 or arm64 processors. However, we have not tested Linux or macOS.

1. Install Java and Python 3.10 if you do not already have them.
2. If you have a newer version of Python than 3.10, download it ([Windows](https://www.python.org/downloads/windows), [Linux](https://www.python.org/downloads/source), [macOS](https://www.python.org/downloads/macos)), add it to path, and create a venv using `py -3.10 -m venv .venv`
3. Install gplaycli: `pip install gplaycli` (see Troubleshooting if you get any errors on first run after install)
4. Enable 2FA on your Google account

## Usage
To use AppScanner, simply run `py AppScanner.py [appID]`

The App ID is the package name. For example: `com.bbc.sounds`, you can get these from the URL bar on Google Play.

For advanced use, see the "Arguments" section below.

The first time you use AppScanner, you may be prompted to enter your Google account credentials. We can't query the Play
Store's APIs without it. You will be prompted to enter your credentials as/when they are needed and given links to
generate App Passwords if required. If you don't want to enter your credentials, you can scan pre-downloaded files
instead (see next section).

### Scanning pre-downloaded apps
If you already have apps downloaded, create a folder named "apps" within the AppScanner directory and put your apps in 
there.

Next, run `py AppScanner.py -s`, passing the `-s` argument to `AppScanner.py`. This will skip the download step and 
begin scanning all files in the apps folder.

### Bulk Downloading
To download multiple apps at once, create a file (for example name it apps.txt) and put an App ID on each line.

Next, run `py AppScanner.py --list=apps.txt` and AppScanner will begin to process the apps.

If you are scanning pre-downloaded files you don't need to include a list file.

### Arguments
| Long                  | Short         | Description                                                                                 |
|-----------------------|---------------|---------------------------------------------------------------------------------------------|
| `--skip-dl`           | `-s`          | Skips the download step, only scanning files already in the "apps" directory.               |
| `--clear-credentials` | `-c`          | Remove saved Google credentials and exit.                                                   |
| `--list=FILENAME`     | `-l=FILENAME` | Pass in a file containing a list of App IDs to be downloaded, see "Bulk Downloading" below. |

### Supported App Types
AppScanner supports Android apps, including those in `.apk`, `.apkm`, `.xapk`, and `.apks` formats.

## Troubleshooting
### GPlayCLI
- You must have 2FA enabled on your Google Account for GPlayCLI to be able to login.
- You must use App Passwords when asked for credentials, not your account password.
- If you have entered the wrong password pass argument `-c` to reset the credential store.
- If you get an error when first running, try the below commands:
```
pip uninstall setuptools -y
pip install "setuptools==68.2.2"
```

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