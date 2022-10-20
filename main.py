#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import pathlib
import sys
import time
from enum import IntEnum, auto, unique
from math import log10
from typing import *

from prompt_toolkit import HTML, PromptSession, print_formatted_text
from prompt_toolkit.shortcuts.progress_bar import ProgressBar
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


BROWSER_BINARY: Final[pathlib.Path] = pathlib.Path("F:\\Programs\\Mozilla Firefox\\firefox.exe").resolve()
DRIVER_BINARY: Final[pathlib.Path] = pathlib.Path("geckodriver.exe").resolve()
PAGE_LOAD_TIME: Final[int] = 1


@unique
class PDFScanError(IntEnum):
    NoError = auto()
    DriverError = auto()
    LoadError = auto()
    PropertiesFetchError = auto()
    ZoomError = auto()
    PaginationError = auto()


@unique
class SessionState(IntEnum):
    Start = auto()
    Login = auto()
    OpenPDF = auto()
    DestinationDirectory = auto()
    PrepareScan = auto()
    ScanPDF = auto()
    AnotherPDF = auto()
    CloseSession = auto()


class ScanException(Exception):

    def __init__(self, code: PDFScanError, message: str = ""):
        self.code: PDFScanError = code
        self.message: str = message


def browser_init_firefox(firefox_path: pathlib.Path, gecko_path: pathlib.Path) -> webdriver.Firefox:
    """Initialize a firefox browser instance"""
    firefox_options: webdriver.FirefoxOptions = webdriver.FirefoxOptions()
    firefox_options.binary_location = str(firefox_path)
    firefox_service: Service = Service(str(gecko_path))
    firefox = webdriver.Firefox(
        service=firefox_service,
        options=firefox_options
    )
    time.sleep(10)
    return firefox


def browser_pdf_load_form_url(driver: webdriver, url: str, timeout: int = 60) -> None:
    """Open a PDF fille and wait until its completely loaded or timeout runs out"""
    # open PDF url
    driver.get(url)

    # wait for document to load
    load_bar = driver.find_element(By.ID, "loadingBar")
    WebDriverWait(driver, timeout=timeout).until(
        expected_conditions.invisibility_of_element(load_bar)
    )


def browser_pdf_fit_page_width(driver: webdriver) -> None:
    driver.find_element(By.ID, "scaleSelect").click()
    driver.find_element(By.ID, "pageWidthOption").click()


def browser_pdf_get_properties(driver: webdriver.Firefox) -> Dict[str, str | int]:
    """Get opened PDF file properties (number of pages and page dimensions in pixels)"""
    pdf_properties: Dict[str, str | int] = dict()

    # get document page count
    page_count = driver.find_element(By.ID, "numPages")
    page_count = int(page_count.text.strip().split()[-1])

    # get document page dimensions
    page_rect = driver.find_element(By.CLASS_NAME, "textLayer").rect

    pdf_properties.update(page_rect)
    pdf_properties["page_count"] = page_count

    return pdf_properties


def browser_pdf_scan_current_page(driver: webdriver.Firefox, save_as: pathlib.Path) -> None:
    """Scan a single PDF page"""
    # save screenshot of current page
    driver.save_screenshot(str(save_as))


def browser_pdf_next_page(driver: webdriver.Firefox) -> None:
    """Scroll to next page in opened PDF file"""
    try:
        driver.find_element(By.ID, "next").click()
    except Exception as exc:
        raise ScanException(PDFScanError.PaginationError, f"Exception {exc} while moving to next page of PDF file")


def run_interactive_cli():
    bottom_text: HTML = HTML("Press CTRL+C to exit")
    dst_directory: pathlib.Path = pathlib.Path()
    session_state: SessionState = SessionState.Start
    ret_code: PDFScanError = PDFScanError.NoError
    pdf_properties: Dict[str, str | int] = dict()
    browser: Optional[webdriver.Firefox] = None
    prompt_session: PromptSession = PromptSession(
        "+------------------------------------------------------------------------------------+\n"
        "| An interactive tool to open PDFs from a URL then save their pages as screenshots.  |\n"
        "|                          To exit at any time press CTRL+C                          |\n"
        "|                    To close when prompted for input press CTRL+D                   |\n"
        "+------------------------------------------------------------------------------------+\n",
        bottom_toolbar=bottom_text
    )

    while True:
        try:
            # Login ---------------------------------------------------------------------------------------------------
            if session_state == SessionState.Start:
                print_formatted_text(prompt_session.message)
                prompt_session.prompt("Press ENTER to open browser...")
                try:
                    browser = browser_init_firefox(BROWSER_BINARY, DRIVER_BINARY)
                except Exception as exc:
                    ret_code = PDFScanError.DriverError
                    session_state = SessionState.CloseSession
                    prompt_session.prompt(f"Failed to open browser, error details: {exc}")
                else:
                    session_state = SessionState.Login

            elif session_state == SessionState.Login:
                prompt_session.prompt("Login to website, press ENTER to continue...")
                session_state = SessionState.OpenPDF

            # Open PDF  -----------------------------------------------------------------------------------------------
            elif session_state == SessionState.OpenPDF:
                prompt_session.prompt("Browse to PDF file, wait for it to load then press ENTER to continue...")
                session_state = SessionState.DestinationDirectory

            # Destination Directory -----------------------------------------------------------------------------------
            elif session_state == SessionState.DestinationDirectory:
                out_dir: str = prompt_session.prompt("Enter directory name where PDF scans will be saved: ")
                if out_dir:
                    dst_directory = pathlib.Path(out_dir).resolve()
                    if dst_directory.exists():
                        confirm: str = prompt_session.prompt(
                            f"Directory {str(dst_directory)} already exists! "
                            f"Enter [y,Y] to confirm using it, any other key to enter a new directory name... "
                        )
                        if confirm not in ("y", "Y"):
                            continue
                    else:
                        confirm: str = prompt_session.prompt(
                            f"Creating directory {str(dst_directory)}, to confirm enter [y/Y]... ")
                        if confirm not in ("y", "Y"):
                            continue

                        try:
                            dst_directory.mkdir(parents=True, exist_ok=True)
                        except Exception as exc:
                            print_formatted_text(f"Directory name is invalid!\nError details: {exc}")
                            continue

                    session_state = SessionState.PrepareScan
                else:
                    print_formatted_text("Cannot create a directory with empty name!")

            # Prepare PDF scan ---------------------------------------------------------------------------------------
            elif session_state == SessionState.PrepareScan:
                try:
                    browser.maximize_window()
                    browser_pdf_fit_page_width(browser)
                    pdf_properties = browser_pdf_get_properties(browser)
                    browser.set_window_size(
                        width=pdf_properties["width"],
                        height=pdf_properties["height"]
                    )
                except ScanException as scan_exc:
                    ret_code = scan_exc.code
                    session_state = SessionState.CloseSession
                else:
                    session_state = SessionState.ScanPDF

            # Scan opened PDF -----------------------------------------------------------------------------------------
            elif session_state == SessionState.ScanPDF:
                pad_size: int = int(log10(pdf_properties["page_count"]))

                with ProgressBar(bottom_toolbar=bottom_text) as progress_bar:
                    for page in progress_bar(range(pdf_properties["page_count"]), label="scan progress"):
                        save_as: pathlib.Path = dst_directory / f"page_{str(page).zfill(pad_size)}.png"
                        try:
                            browser_pdf_scan_current_page(browser, save_as)
                            browser_pdf_next_page(browser)
                            time.sleep(1)
                        except Exception as exc:
                            print_formatted_text(exc)
                            sys.exit(-3)

                print_formatted_text("PDF file scanned successfully. ")
                print_formatted_text("--------------------------------------------------------------------------------")
                session_state = session_state.AnotherPDF

            # Scan another PDF ? --------------------------------------------------------------------------------------
            elif session_state == SessionState.AnotherPDF:
                another: str = prompt_session.prompt(
                    "Enter [y/Y] to scan another PDF... "
                )
                if another in ("y", "Y"):
                    session_state = SessionState.OpenPDF
                else:
                    session_state = session_state.CloseSession

            # Close session -------------------------------------------------------------------------------------------
            elif session_state == SessionState.CloseSession:
                browser.quit()
                print_formatted_text("--------------------------------------------------------------------------------")
                print_formatted_text("Done")
                if ret_code == PDFScanError.NoError:
                    sys.exit(0)
                else:
                    sys.exit(-1)

        except (KeyboardInterrupt, EOFError) as prompt_exc:
            if browser:
                browser.quit()
            sys.exit(-1)


def main():
    run_interactive_cli()


if __name__ == '__main__':
    main()
