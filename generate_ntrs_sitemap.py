#!/usr/bin/env python3
"""
Generate comprehensive XML sitemaps for the NASA Technical Reports Server (NTRS).
Indexes:
  1. Historical Full-Text PDFs (1914-2009, ~218,000 URLs, modern era excluded to prevent duplicate Onyx ingestion)
  2. Modern Era PDFs (2010-2026, ~79,000 direct NASA-hosted PDF URLs)
  3. Complete Master Full-Text PDFs (~297,000 direct NASA-hosted PDF URLs)
  4. Metadata/Abstract Citations (~305,000 NTRS landing/abstract pages)
Outputs:
  - ntrs_sitemap.xml (Root Master Sitemap Index)
  - ntrs_pdf_sitemap.xml (Historical PDF Sitemap Index: chunks 1..11)
  - sitemaps/pdf/ntrs_pdf_1.xml ... 11.xml (20k URLs each, Historical 1914-2009)
  - sitemaps/pdf/ntrs_pdf_modern.xml (Modern PDFs 2010-2026)
  - ntrs_pdf_all.xml (Flat Historical PDFs for Onyx Web Connector, modern excluded)
  - ntrs_pdf_historical.xml (Flat Historical PDFs, modern excluded)
  - ntrs_pdf_complete.xml (Flat Complete Full-Text PDFs 1914-2026)
  - ntrs_citations_sitemap.xml (Citations Sitemap Index)
  - sitemaps/citations/ntrs_citations_1.xml ... 7.xml (50k URLs each)
  - ntrs_citations_all.xml (Flat All Citations)
  - ntrs_all.xml (Unified Flat All Records: All PDFs + Citations)
  - Plain-text URL lists (.txt)
"""

import os
import re
import gzip
import time
import json
import datetime
from concurrent.futures import ThreadPoolExecutor
import requests

GITHUB_RAW_BASE = "https://raw.githubusercontent.com/Oht8wooWi8yait9n/ntrs/main"
NTRS_API_SEARCH = "https://ntrs.nasa.gov/api/citations/search"
NTRS_SITEMAP_INDEX = "https://ntrs.nasa.gov/sitemap.xml"
PDF_CHUNK_SIZE = 20000  # 20k URLs per sitemap (~24h embedding window in Onyx)
CITATIONS_CHUNK_SIZE = 50000

def get_iso_date():
    return datetime.date.today().isoformat()

def step1_fetch_all_citation_ids(base_dir=None):
    """Download official NTRS sitemaps and extract all citation IDs with retry and cache fallback."""
    print("=== Step 1: Downloading 116 official NTRS sitemaps ===")
    t0 = time.time()
    sitemap_urls = []
    try:
        resp = requests.get(NTRS_SITEMAP_INDEX, timeout=20)
        if resp.status_code == 200:
            sitemap_urls = re.findall(r'<loc>(https://ntrs\.nasa\.gov/sitemap-[^<]+)</loc>', resp.text)
    except Exception as e:
        print(f"  Warning: Could not fetch NTRS sitemap index: {e}")

    print(f"Found {len(sitemap_urls)} sub-sitemaps in official index.")

    def parse_sub(url):
        for attempt in range(5):
            try:
                r = requests.get(url, timeout=25)
                if r.status_code == 200:
                    text = gzip.decompress(r.content).decode("utf-8")
                    return re.findall(r'<loc>https://ntrs\.nasa\.gov/citations/(\d+)</loc>', text)
                elif r.status_code == 429:
                    time.sleep(2 * (attempt + 1))
            except Exception:
                time.sleep(1 + attempt)
        print(f"  [!] Failed to fetch {url} after 5 attempts.")
        return []

    all_ids = set()
    if sitemap_urls:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for ids in ex.map(parse_sub, sitemap_urls):
                all_ids.update(ids)

    # Cache fallback / safety check: If network issues dropped sitemaps, supplement from existing local files
    if base_dir and len(all_ids) < 550000:
        print(f"  [!] Warning: Harvested {len(all_ids):,} IDs (< 550k expected). Loading fallback IDs from local files...")
        cache_gz = os.path.join(base_dir, "ntrs_cache.json.gz")
        if os.path.exists(cache_gz):
            try:
                with gzip.open(cache_gz, "rt", encoding="utf-8") as f:
                    cdata = json.load(f)
                    all_ids.update(cdata.keys())
            except Exception:
                pass
        cit_txt = os.path.join(base_dir, "ntrs_citations_urls.txt")
        if os.path.exists(cit_txt):
            try:
                with open(cit_txt, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            cid = line.rstrip("/").split("/")[-1]
                            if cid.isdigit():
                                all_ids.add(cid)
            except Exception:
                pass
        print(f"  Restored total IDs to {len(all_ids):,} using local fallback cache.")

    dt = time.time() - t0
    print(f"Step 1 Complete: Extracted {len(all_ids):,} total unique citation IDs in {dt:.2f}s.\n")
    return all_ids

def query_partition(item):
    name, body, year = item
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(NTRS_API_SEARCH, json=body, timeout=45)
            if r.status_code == 200:
                results = r.json().get("results", [])
                extracted = []
                for doc in results:
                    cid = str(doc.get("id", ""))
                    downloads = doc.get("downloads", [])
                    for d in downloads:
                        pdf_rel = d.get("links", {}).get("pdf")
                        if pdf_rel and pdf_rel.endswith(".pdf"):
                            full_url = f"https://ntrs.nasa.gov{pdf_rel}"
                            extracted.append((cid, full_url, year))
                            break
                return extracted
            elif r.status_code == 429:
                time.sleep(2 * (attempt + 1))
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  Error querying {name}: {e}")
            time.sleep(1)
    return []

def step2_harvest_full_text_pdfs(cache_file_gz=None, cache_file_json=None, force_refresh=False):
    """Load cached PDF links from gzip (or JSON) and incrementally harvest new PDFs for recent years."""
    pdf_dict = {}
    loaded = False

    # 1. Try loading from compressed gzip cache
    if cache_file_gz and os.path.exists(cache_file_gz) and not force_refresh:
        try:
            print(f"Loading cached PDF links from {cache_file_gz}...")
            with gzip.open(cache_file_gz, "rt", encoding="utf-8") as f:
                pdf_dict = json.load(f)
            print(f"Loaded {len(pdf_dict):,} cached PDF records from gzip cache.\n")
            loaded = True
        except Exception as e:
            print(f"Gzip cache load failed ({e}), checking uncompressed cache...")

    # 2. Try loading from uncompressed JSON cache if gzip not available
    if not loaded and cache_file_json and os.path.exists(cache_file_json) and not force_refresh:
        try:
            print(f"Loading cached PDF links from {cache_file_json}...")
            with open(cache_file_json, "r", encoding="utf-8") as f:
                pdf_dict = json.load(f)
            print(f"Loaded {len(pdf_dict):,} cached PDF records from JSON cache.\n")
            loaded = True
        except Exception as e:
            print(f"JSON cache load failed ({e}), harvesting fresh from API...")

    this_year = datetime.date.today().year

    # 3. If loaded, do an incremental check for recent years (current year and previous year)
    if loaded:
        print(f"=== Incremental Check: Checking NTRS API for new {this_year-1}..{this_year} publications ===")
        inc_tasks = []
        for y in range(this_year - 1, this_year + 1):
            inc_tasks.append((f"pub_{y}", {
                "page": {"size": 10000},
                "index": ["submissions*"],
                "disseminated": ["DOCUMENT_AND_METADATA"],
                "published": {"gte": f"{y}-01-01T00:00:00", "lte": f"{y}-12-31T23:59:59"}
            }, y))
            inc_tasks.append((f"cre_{y}", {
                "page": {"size": 10000},
                "index": ["submissions*"],
                "disseminated": ["DOCUMENT_AND_METADATA"],
                "created": {"gte": f"{y}-01-01T00:00:00", "lte": f"{y}-12-31T23:59:59"}
            }, y))

        new_count = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            for batch in ex.map(query_partition, inc_tasks):
                for cid, pdf_url, year in batch:
                    if cid not in pdf_dict:
                        pdf_dict[cid] = [pdf_url, year]
                        new_count += 1

        print(f"Incremental check complete: Added {new_count:,} new PDF records.")
        if cache_file_gz:
            try:
                with gzip.open(cache_file_gz, "wt", encoding="utf-8") as f:
                    json.dump(pdf_dict, f)
                print(f"Saved {len(pdf_dict):,} records to gzip cache {cache_file_gz}\n")
            except Exception as e:
                print(f"Warning: Could not save gzip cache: {e}\n")

        return pdf_dict

    # 4. If not loaded, full harvest across 1914 to this_year + 1
    print("=== Step 2: Harvesting direct full-text PDF links from NTRS API ===")
    t0 = time.time()

    tasks = []
    # Published years 1914 to this_year + 1
    for y in range(1914, this_year + 2):
        body = {
            "page": {"size": 10000},
            "index": ["submissions*"],
            "disseminated": ["DOCUMENT_AND_METADATA"],
            "published": {"gte": f"{y}-01-01T00:00:00", "lte": f"{y}-12-31T23:59:59"}
        }
        tasks.append((f"pub_{y}", body, y))

    # Created years 2014 to this_year
    for y in range(2014, this_year + 1):
        body = {
            "page": {"size": 10000},
            "index": ["submissions*"],
            "disseminated": ["DOCUMENT_AND_METADATA"],
            "created": {"gte": f"{y}-01-01T00:00:00", "lte": f"{y}-12-31T23:59:59"}
        }
        tasks.append((f"cre_{y}", body, y))

    print(f"Dispatching {len(tasks)} partition queries with ThreadPoolExecutor...")

    with ThreadPoolExecutor(max_workers=8) as ex:
        for batch in ex.map(query_partition, tasks):
            for cid, pdf_url, year in batch:
                if cid not in pdf_dict:
                    pdf_dict[cid] = [pdf_url, year]

    dt = time.time() - t0
    print(f"Step 2 Complete: Harvested {len(pdf_dict):,} citations with direct PDF links in {dt:.2f}s.\n")

    if cache_file_gz:
        try:
            with gzip.open(cache_file_gz, "wt", encoding="utf-8") as f:
                json.dump(pdf_dict, f)
            print(f"Saved {len(pdf_dict):,} PDF links to gzip cache {cache_file_gz}\n")
        except Exception as e:
            print(f"Could not write gzip cache file: {e}\n")

    return pdf_dict

def write_urlset_xml(filepath, urls, lastmod, compress=False):
    """Write standard urlset XML conforming to sitemaps.org (supports gzip compression).
    Preserves existing files without rewriting if the URL list has not changed."""
    actual_path = filepath if (filepath.endswith(".gz") or not compress) else filepath + ".gz"

    # Check if existing file has identical URLs to avoid bumping lastmod and polluting git diffs
    if os.path.exists(actual_path):
        try:
            if actual_path.endswith(".gz"):
                with gzip.open(actual_path, "rt", encoding="utf-8") as f:
                    content = f.read()
            else:
                with open(actual_path, "r", encoding="utf-8") as f:
                    content = f.read()
            existing_locs = re.findall(r'<loc>([^<]+)</loc>', content)
            if existing_locs == urls:
                return actual_path
        except Exception:
            pass

    os.makedirs(os.path.dirname(actual_path) or ".", exist_ok=True)
    open_fn = (lambda p: gzip.open(p, "wt", encoding="utf-8")) if (compress or actual_path.endswith(".gz")) else (lambda p: open(p, "w", encoding="utf-8"))
    with open_fn(actual_path) as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            f.write("  <url>\n")
            f.write(f"    <loc>{u}</loc>\n")
            f.write(f"    <lastmod>{lastmod}</lastmod>\n")
            f.write("    <changefreq>monthly</changefreq>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")
    return actual_path

def write_sitemapindex_xml(filepath, sub_sitemap_urls, lastmod):
    """Write standard sitemapindex XML referencing sub-sitemaps."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            existing_subs = re.findall(r'<loc>([^<]+)</loc>', content)
            if existing_subs == sub_sitemap_urls:
                return
        except Exception:
            pass

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for s in sub_sitemap_urls:
            f.write("  <sitemap>\n")
            f.write(f"    <loc>{s}</loc>\n")
            f.write(f"    <lastmod>{lastmod}</lastmod>\n")
            f.write("  </sitemap>\n")
        f.write("</sitemapindex>\n")

def write_txt_list(filepath, urls):
    """Write plain text URL list, preserving existing file if content is identical."""
    content = "\n".join(urls) + "\n"
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                if f.read() == content:
                    return
        except Exception:
            pass
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    start_time = time.time()
    today = get_iso_date()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_file_gz = os.path.join(base_dir, "ntrs_cache.json.gz")
    cache_file_json = os.path.join(base_dir, "ntrs_cache.json")

    # 1. Fetch all citation IDs (with retry and local cache fallback)
    all_citation_ids = step1_fetch_all_citation_ids(base_dir=base_dir)

    # 2. Harvest all PDF URLs (uses local gzip cache if available, incrementally updates recent years)
    pdf_dict = step2_harvest_full_text_pdfs(cache_file_gz=cache_file_gz, cache_file_json=cache_file_json)

    # 3. Categorize URLs
    print("=== Step 3: Categorizing and partitioning URLs ===")
    all_pdf_urls = []
    modern_pdf_urls = []
    historical_pdf_urls = []
    citation_urls = []

    # Sort citations deterministically (newest first)
    sorted_all_ids = sorted(all_citation_ids, reverse=True)

    for cid in sorted_all_ids:
        if cid in pdf_dict:
            pdf_url, year = pdf_dict[cid]
            all_pdf_urls.append(pdf_url)
            if year >= 2010:
                modern_pdf_urls.append(pdf_url)
            else:
                historical_pdf_urls.append(pdf_url)
        else:
            citation_urls.append(f"https://ntrs.nasa.gov/citations/{cid}")

    print(f"Total Full-Text PDF URLs: {len(all_pdf_urls):,}")
    print(f"  Modern Era (2010-2026) PDFs: {len(modern_pdf_urls):,}")
    print(f"  Historical (1914-2009) PDFs: {len(historical_pdf_urls):,}")
    print(f"Total Metadata/Abstract URLs: {len(citation_urls):,}")
    print(f"Combined Total URLs: {len(all_pdf_urls) + len(citation_urls):,}")

    # Safety Check: Prevent publishing corrupted or truncated sitemaps
    if len(all_pdf_urls) < 250000 or len(citation_urls) < 250000:
        raise RuntimeError(
            f"Safety check aborted: Found only {len(all_pdf_urls):,} PDFs and {len(citation_urls):,} citations "
            f"(expected ~297k PDFs and ~305k citations). Aborting to prevent sitemap corruption!"
        )

    # 4. Generate PDF Sitemaps (Historical chunks of 20k, modern excluded)
    print("\n=== Step 4: Generating PDF Sitemaps ===")
    pdf_sub_urls = []
    pdf_chunks = [historical_pdf_urls[i:i + PDF_CHUNK_SIZE] for i in range(0, len(historical_pdf_urls), PDF_CHUNK_SIZE)]
    for idx, chunk in enumerate(pdf_chunks, 1):
        rel_path = f"sitemaps/pdf/ntrs_pdf_{idx}.xml"
        file_path = os.path.join(base_dir, rel_path)
        write_urlset_xml(file_path, chunk, today)
        raw_url = f"{GITHUB_RAW_BASE}/{rel_path}"
        pdf_sub_urls.append(raw_url)
        print(f"  Wrote {rel_path} ({len(chunk):,} URLs)")

    # Clean up obsolete historical chunk files (e.g. ntrs_pdf_12.xml if it existed)
    chunk_idx = len(pdf_chunks) + 1
    while True:
        old_chunk = os.path.join(base_dir, f"sitemaps/pdf/ntrs_pdf_{chunk_idx}.xml")
        if os.path.exists(old_chunk):
            os.remove(old_chunk)
            print(f"  Removed obsolete {old_chunk}")
            chunk_idx += 1
        else:
            break

    # PDF Modern Sitemap (2010-2026)
    modern_rel = "sitemaps/pdf/ntrs_pdf_modern.xml"
    write_urlset_xml(os.path.join(base_dir, modern_rel), modern_pdf_urls, today)
    print(f"  Wrote {modern_rel} ({len(modern_pdf_urls):,} URLs)")

    # PDF Sitemap Index (Historical chunks 1..11)
    write_sitemapindex_xml(os.path.join(base_dir, "ntrs_pdf_sitemap.xml"), pdf_sub_urls, today)
    print(f"  Wrote ntrs_pdf_sitemap.xml ({len(pdf_sub_urls)} sub-sitemaps)")

    # Unified Flat PDF Sitemap (Historical PDFs for Onyx Web Connector, modern 2010-2026 excluded, 37MB)
    write_urlset_xml(os.path.join(base_dir, "ntrs_pdf_all.xml"), historical_pdf_urls, today)
    print(f"  Wrote ntrs_pdf_all.xml ({len(historical_pdf_urls):,} URLs - Modern 2010-2026 excluded)")

    # Complete master of all PDFs (compressed .xml.gz to keep under GitHub 50MB limit)
    write_urlset_xml(os.path.join(base_dir, "ntrs_pdf_complete.xml.gz"), all_pdf_urls, today, compress=True)
    print(f"  Wrote ntrs_pdf_complete.xml.gz ({len(all_pdf_urls):,} URLs, compressed ~2.4MB)")

    # Remove obsolete uncompressed files exceeding GitHub's 50MB threshold
    for obsolete in ["ntrs_all.xml", "ntrs_pdf_complete.xml", "ntrs_pdf_historical.xml"]:
        old_p = os.path.join(base_dir, obsolete)
        if os.path.exists(old_p):
            os.remove(old_p)
            print(f"  Removed obsolete uncompressed file: {obsolete}")

    # 5. Generate Citations Sitemaps (Chunks of 50k)
    print("\n=== Step 5: Generating Citations Sitemaps ===")
    cit_sub_urls = []
    cit_chunks = [citation_urls[i:i + CITATIONS_CHUNK_SIZE] for i in range(0, len(citation_urls), CITATIONS_CHUNK_SIZE)]
    for idx, chunk in enumerate(cit_chunks, 1):
        rel_path = f"sitemaps/citations/ntrs_citations_{idx}.xml"
        file_path = os.path.join(base_dir, rel_path)
        write_urlset_xml(file_path, chunk, today)
        raw_url = f"{GITHUB_RAW_BASE}/{rel_path}"
        cit_sub_urls.append(raw_url)
        print(f"  Wrote {rel_path} ({len(chunk):,} URLs)")

    # Citations Sitemap Index
    write_sitemapindex_xml(os.path.join(base_dir, "ntrs_citations_sitemap.xml"), cit_sub_urls, today)
    print(f"  Wrote ntrs_citations_sitemap.xml ({len(cit_sub_urls)} sub-sitemaps)")

    # Unified Flat Citations Sitemap (All 305k Citations for Onyx Web Connector, 43MB)
    write_urlset_xml(os.path.join(base_dir, "ntrs_citations_all.xml"), citation_urls, today)
    print(f"  Wrote ntrs_citations_all.xml ({len(citation_urls):,} URLs)")

    # 6. Generate Master Sitemap Index (Modern + Historical PDFs + Citations)
    print("\n=== Step 6: Generating Master Sitemap Index ===")
    master_subs = [f"{GITHUB_RAW_BASE}/sitemaps/pdf/ntrs_pdf_modern.xml"] + pdf_sub_urls + cit_sub_urls
    write_sitemapindex_xml(os.path.join(base_dir, "ntrs_sitemap.xml"), master_subs, today)
    print(f"  Wrote ntrs_sitemap.xml ({len(master_subs)} total sub-sitemaps)")

    # Unified Flat Master Sitemap (compressed .xml.gz to keep under GitHub 50MB limit)
    write_urlset_xml(os.path.join(base_dir, "ntrs_all.xml.gz"), all_pdf_urls + citation_urls, today, compress=True)
    print(f"  Wrote ntrs_all.xml.gz ({len(all_pdf_urls) + len(citation_urls):,} URLs, compressed ~3.4MB)")

    # 7. Write Plain Text URL Lists
    print("\n=== Step 7: Writing Plain Text URL Lists ===")
    write_txt_list(os.path.join(base_dir, "ntrs_pdf_urls.txt"), historical_pdf_urls)
    write_txt_list(os.path.join(base_dir, "ntrs_pdf_historical_urls.txt"), historical_pdf_urls)
    write_txt_list(os.path.join(base_dir, "ntrs_pdf_modern_urls.txt"), modern_pdf_urls)
    write_txt_list(os.path.join(base_dir, "ntrs_pdf_complete_urls.txt"), all_pdf_urls)
    write_txt_list(os.path.join(base_dir, "ntrs_citations_urls.txt"), citation_urls)
    write_txt_list(os.path.join(base_dir, "ntrs_all_urls.txt"), all_pdf_urls + citation_urls)
    print("  Wrote plain text URL lists.")

    total_time = time.time() - start_time
    print(f"\nAll operations completed successfully in {total_time:.2f}s ({total_time / 60:.2f} mins).")

if __name__ == "__main__":
    main()
