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


## Note

- If you're using windows, open file `run.bat`, set `FFOX_BIN` to firefox executable path,`GECKO_BIN` to geckodriver executable path and `PAGE_WAIT` to PDF page wait time. After that you can run the tool by running `run.bat` either from a command line or by double-clicking it
