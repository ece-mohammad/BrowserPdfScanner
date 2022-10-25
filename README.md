# Browser PDF Scanner

An interactive CLI tool to scan an open PDF from a browser instance. The tool opens an automated browser instance then screenshots all PDF pages into a destination folder. 

Why? Usually you can download PDFs from within the browser by clicking on the download button or `CTRL+s`. Except for some reasons, some websites prevent you from doing that and may go to such lengths as blocking your account if you try to download a PDF file you already paid for. So, here we are. I made this tool for a friend because their school blocked downloading their PDF books.


## Requirements

- Python 3.10
- Firefox: currently this tool only supports firefox 
- Geckodriver: Driver used ny selenium to automate Firefox browser instance. The latest version of geckodriver is compatible with the latest version of Firefox. If you have an older Firefox, to know what version of geckodriver is compatible with your Firefox version [check here](https://firefox-source-docs.mozilla.org/testing/geckodriver/Support.html). 


## Setup

- Download the repository and unzip the compressed file then `cd` into the repo folder, or clone it
    
    ```shell
    git clone https://github.com/ece-mohammad/BrowserPdfScanner.git browser_pdf_scanner
    cd browser_pdf_scanner    
    ```
  
- Install `virtualenv` package (if it's not already  installed)
- 
  ```shell
  pip install virtualenv
  ```
  
  or (if pip is not in PATH)
- 
  ```shell
  python -m pip install virtualenv
  ```

- Setup a python virtual environment

    ```shell
    python -m virtualenv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```

- Run it

    ```shell
    python main.py [path_to_firefox_executable] [path_to_gecko_driver_executable]
    ```

## Notes

- If you're using windows, open file `run.bat`, set `FFOX_BIN` to firefox executable path,`GECKO_BIN` to geckodriver executable path and `PAGE_WAIT` to PDF page wait time. After that you can run the tool by running `run.bat` either from a command line or by double-clicking it

- The interactive tool will launch an automated instance of firefox, that you can interact with. While You'll need to browse to the PDF file directly (log in to website if required, then open PDF file inside the browser).

- Make sure the tab in which the PDF is open is the first tab. That means you can open multiple PDF files in the same browser window, and drag the PDF you want to scan to tab `#1`.

- When the tool is taking screenshots, DO NOT  minimize the browser instance or change current tab. You can send it to the background `Win+D` on Windows (show desktop), or open it in a separate workspace and leave it there.

- The interactive tool will resize the browser window, do not resize/maximize the browser window until it's done. The tool scales PDF pages to fit page width. This introduces the problem of having a single PDF page split between 2 or 3 pages. This is solved by resizing browser window to fit PDF page in a single page. If you resize the browser window, you will get a screenshot of the first third or half of each page.

- Some tag searching I've used is not optimal (because guess what? they changed the tags ID's and some tag names!). 
