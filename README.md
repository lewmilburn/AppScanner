# AppScanner

AppScanner is a security testing tool that downloads, decompiles, and scans Android applications. Once scanned, the
script then generates a JSON report that can be used into other tools and a HTML report that can be opened in your
browser and shared with others.

The JSON report contains raw and redacted credentials (if any are found), the HTML report only contains redacted 
credentials.

## Requirements & Setup
> :warning: Please note that downloading lots of apps will result in high disk usage and increases the chance that you are blocked from the service.

AppScanner supports Windows (10 build 1511 or newer), Linux, and macOS devices running on amd64 or arm64 processors. 
However, we have not tested 
the tool on Linux or macOS.

AppScanner requires cURL to work, it is bundled with most operating systems, but may need installing if you don't 
already have it.

If you download a lot of apps, a lot of disk space will be used.

Windows: If it does not run in PowerShell, try the standard command prompt.

## Usage
To download a single app using AppScanner, simply run `py AppScanner.py -a=[appID]`

The App ID is the package name. For example: `com.bbc.sounds`, you can get these from the URL bar on Google Play.

To download multiple apps, use one of the search options below:

**You MUST pass ONE of the following arguments:**

| Long               | Short | Example                                | Description                                                                          |
|--------------------|-------|----------------------------------------|--------------------------------------------------------------------------------------|
| `--app`            | `-a`  | `py AppScanner.py -a=com.bbc.sounds`   | Downloads an APK package.                                                            |
| `--search`         | `-q`  | `py AppScanner.py -q="BBC Sounds"`     | Searches for APK packages.                                                           |
| `--categoryList`   | `-cl` | `py AppScanner.py -cl`                 | Gets a list of all available APK categories, then allows you to search one.          |
| `--categorySearch` | `-cs` | `py AppScanner.py -cs="entertainment"` | Search APKPure for apps in a specific category.                                      |
| `--list=FILENAME`  | `-l`  | `py AppScanner.py -l`                  | Pass in a AppList to be downloaded, see "Bulk Downloading" below.                    |
| `--skip-dl`        | `-s`  | `py AppScanner.py -s`                  | Skips the download/search step, only scanning files already in the "apps" directory. |

**You may also pass one of the following arguments if required:**

| Long          | Short | Example                                 | Description                                                                                                                                                                                                                                                                                                  |
|---------------|-------|-----------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `--keep`      | `-k`  | `py AppScanner.py -a=com.bbc.sounds -k` | After scanning AppScanner automatically deletes APKs to free up disk space, passing this argument stops them from being deleted. This may result in considerably higher disk usage.                                                                                                                          |
| `--save-list` | `-v`  | `py AppScanner.py -cl --save-list`      | Instead of downloading the apps right away, AppScanner will create a wordlist. This allows you to select apps from multiple categories and then pass the list in using the --list flag instead. If file exists, it will ask you if you want to overwrite or append. This example will search all categories. |

## Bulk Downloading
### Using keyword or category search
You can download multiple apps by searching for the app's keyword or category.
If you need to search for multiple apps with different keywords or categories, use AppLists.

When searching for a keyword or category, you will be prompted to select the apps you wish to download, you can download
multiple here. Keyword searches tend to have limited results, whereas category searches may have a few hundred results.

You can download the entire selection by entering 'all' when prompted to make a selection.

### AppLists
#### What are AppLists?
An AppList is simply a list of application IDs, one on each line, that is passed into AppScanner. The application IDs 
correspond with the app's package. For example: `com.bbc.sounds`.
AppLists allow you to download a list of apps that would typically require multiple separate keyword or category searches 
into a single report as an alternative to `--skip-dl`.

There is no limit to how many apps can be in an AppList, but please be aware that the more apps you download the more 
disk space will be used.

#### Creating an AppList
To create an AppList (which is especially helpful when you need to search across multiple keywords or categories) you 
can pass `--save-list=example.txt` into AppScanner for it to save your selection to an AppList instead of processing it.
Apps will not be scanned when this flag is sent, only downloaded. Next, conduct any additional searches you require,
also saving them to the same file (it will ask you if you want to overwrite or append the file).

#### Using AppLists
First, create an AppList. Then run `py AppScanner.py --list=example.txt` (with your AppList being example.txt) for 
AppScanner to download all of the files you have previously searched for.

### Using pre-downloaded apps
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
- This version of AppScanner is bundled with Trufflehog 3.94.1, if you update it delete all of the Trufflehog binaries, delete installed.conf, and drop the new .tar.gz files in the libs folder, do not rename them. We will periodically update Trufflehog for you.
- Checksums for the binaries are available at https://github.com/trufflesecurity/trufflehog/releases/tag/v3.94.1
- Not running? Try `chmod +x /libs/trufflehog_[OS]` if on Linux/macOS.
- Trufflehog is distributed with AppScanner and will be extracted automatically on first run.

## Roadmap
- App ID searching