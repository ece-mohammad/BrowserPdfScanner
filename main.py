#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import pathlib
import sys
import time
from enum import IntEnum, auto, unique
from math import log10
from typing import *
from urllib import parse

from prompt_toolkit import HTML, PromptSession, print_formatted_text
from prompt_toolkit.shortcuts.progress_bar import ProgressBar
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait


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


def browser_reset_window_size(driver: webdriver.Firefox) -> None:
    """Reset browser's window size"""
    driver.minimize_window()
    # time.sleep(1)
    driver.maximize_window()
    # time.sleep(1)


def browser_pdf_locate_tabs(driver: webdriver.Firefox) -> Dict[str, str | Dict[int, Dict[str, str]]]:
    """Locate PDF file's tab"""
    pdf_tabs: Dict[int, Dict[str, str]] = dict()
    original_tab: str = driver.current_window_handle

    for tab_num, tab_handle in enumerate(driver.window_handles):
        driver.switch_to.window(tab_handle)
        tab_url: str = driver.current_url
        if parse.urlparse(tab_url).path.endswith("pdf"):
            pdf_tabs[tab_num] = {
                "title":  driver.title,
                "url":    driver.current_url,
                "handle": tab_handle
            }

    driver.switch_to.window(original_tab)
    return {"current_tab": driver.current_window_handle, "pdf_tabs": pdf_tabs}


def browser_pdf_fit_page_width(driver: webdriver) -> None:
    """scale PDF page to fit window width"""
    scale_options = driver.find_elements(By.TAG_NAME, "option")
    if not scale_options:
        return

    for option in scale_options:
        if option.get_attribute("value") == "page-width":
            option.click()

    # time.sleep(1)


def browser_pdf_fit_page_height(driver: webdriver.Firefox, pdf_properties: Dict[str, int | float]) -> None:
    """resize browser instance's window to fit PDF page height"""
    browser_rect: Dict[str, int | float] = driver.get_window_rect()
    browser_rect["height"] = pdf_properties["y"] + pdf_properties["height"]
    driver.set_window_rect(**browser_rect)
    # time.sleep(1)


def browser_pdf_goto_start(driver: webdriver.Firefox) -> None:
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.HOME)
    # time.sleep(1)


def browser_pdf_get_properties(driver: webdriver.Firefox) -> Dict[str, str | int]:
    """Get opened PDF file properties (number of pages and page dimensions in pixels)"""
    pdf_properties: Dict[str, str | int] = dict()

    # get document page count
    page_count = driver.find_element(By.ID, "numPages")
    page_count = int(page_count.text.strip().split()[-1])

    # get document page dimensions
    page_rect = driver.find_element(By.CLASS_NAME, "page").rect
    pdf_properties.update(page_rect)
    pdf_properties["page_count"] = page_count

    return pdf_properties


def browser_pdf_scan_current_page(driver: webdriver.Firefox, save_as: pathlib.Path) -> None:
    """Scan a single PDF page"""
    # save screenshot of current page
    # driver.save_screenshot(str(save_as))
    driver.save_full_page_screenshot(str(save_as))


def browser_pdf_next_page(driver: webdriver.Firefox) -> None:
    """Scroll to next page in opened PDF file"""
    try:
        driver.find_element(By.CSS_SELECTOR, "button[title='Next Page']").click()
    except Exception as exc:
        raise ScanException(PDFScanError.PaginationError, f"Exception {exc} while moving to next page of PDF file")


def run_interactive_cli(firefox_binary: pathlib.Path, geckodriver_binary: pathlib.Path, page_load_time: int = 1):
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
                    browser = browser_init_firefox(firefox_binary, geckodriver_binary)
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
                prompt_session.prompt(
                    "Browse to PDF file, "
                    "wait for it to load, "
                    "set PDF tab as first tab "
                    "then press ENTER to continue..."
                )

                open_tabs: Dict[str, str | Dict[int, Dict[str, str]]] = browser_pdf_locate_tabs(browser)
                pdf_tabs: Dict[int, Dict[str, str]] = open_tabs.get("pdf_tabs", {})

                if len(pdf_tabs) == 0:
                    print_formatted_text("Didn't find any open PDF files...")
                    session_state = SessionState.OpenPDF

                else:
                    (tab_index, tab_info) = pdf_tabs.popitem()
                    print_formatted_text(f"Found PDF file: {tab_info['title']} in tab #{tab_index + 1}")
                    browser.switch_to.window(tab_info["handle"])
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
                    browser_reset_window_size(browser)
                    browser_pdf_fit_page_width(browser)
                    pdf_properties = browser_pdf_get_properties(browser)
                    browser_pdf_fit_page_height(browser, pdf_properties)
                    browser_pdf_goto_start(browser)
                except ScanException as scan_exc:
                    print(f"{scan_exc=}")
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
                        browser_pdf_scan_current_page(browser, save_as)
                        browser_pdf_next_page(browser)
                        time.sleep(page_load_time)

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
                if browser:
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
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument(
        "firefox_binary",
        help="Path to Firefox executable",
        type=pathlib.Path,
    )

    arg_parser.add_argument(
        "geckodriver_binary",
        help="Path to geckodriver executable",
        type=pathlib.Path,
    )

    arg_parser.add_argument(
        "-w", "--page_load_time",
        help="time to wait (in seconds) for PDF page to load after it's scrolled into view",
        type=int,
        default=1
    )

    args = arg_parser.parse_args()

    firefox_binary: pathlib.Path = args.firefox_binary
    geckodriver_binary: pathlib.Path = args.geckodriver_binary
    page_load_time: int = args.page_load_time

    try:
        firefox_binary = firefox_binary.resolve(strict=True)
        geckodriver_binary = geckodriver_binary.resolve(strict=True)
    except Exception as exc:
        print(f"Invalid path to firefox or geckodriver executables")
    else:
        run_interactive_cli(firefox_binary, geckodriver_binary, page_load_time)


if __name__ == '__main__':
    main()
