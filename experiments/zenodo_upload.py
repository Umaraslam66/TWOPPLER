"""Upload the DOPPLER write-up PDFs to Zenodo and, on request, publish them for a DOI.

Metadata comes from experiments/zenodo_metadata.json; the API token comes from .env at the
repo root (ZENODO_TOKEN, or ZENODO_SANDBOX_TOKEN with --sandbox). Standard library only, so
the project gains no new dependency. The default action creates or updates a DRAFT and prints
its URL for human review. Nothing becomes public without --publish.

Deposition state is written to results/zenodo_deposition.json keyed by host, so re-runs update
the same draft instead of creating duplicate records. Sandbox and production are separate
entries and never mix.

Run:
  python experiments/zenodo_upload.py --dry-run                 validate only, no network
  python experiments/zenodo_upload.py --sandbox                 draft on sandbox.zenodo.org
  python experiments/zenodo_upload.py                           draft on zenodo.org
  python experiments/zenodo_upload.py --publish                 publish the draft, mint the DOI
  python experiments/zenodo_upload.py --new-version --publish   new version of a published record

API surface used (legacy deposit API, checked against https://developers.zenodo.org on
2026-07-29): POST /api/deposit/depositions, PUT {links.bucket}/{filename} with raw bytes,
PUT /api/deposit/depositions/:id, POST /api/deposit/depositions/:id/actions/publish,
POST /api/deposit/depositions/:id/actions/newversion.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / ".env"
METADATA_PATH = REPO_ROOT / "experiments" / "zenodo_metadata.json"
STATE_PATH = REPO_ROOT / "results" / "zenodo_deposition.json"

PROD_HOST = "zenodo.org"
SANDBOX_HOST = "sandbox.zenodo.org"
TOKEN_KEYS = {PROD_HOST: "ZENODO_TOKEN", SANDBOX_HOST: "ZENODO_SANDBOX_TOKEN"}

UPLOAD_TYPES = {
    "publication", "poster", "presentation", "dataset", "image", "video", "software",
    "lesson", "physicalobject", "other",
}
PUBLICATION_TYPES = {
    "annotationcollection", "book", "section", "conferencepaper", "datamanagementplan",
    "article", "patent", "preprint", "deliverable", "milestone", "proposal", "report",
    "softwaredocumentation", "taxonomictreatment", "technicalnote", "thesis",
    "workingpaper", "other",
}
CONTRIBUTOR_TYPES = {
    "ContactPerson", "DataCollector", "DataCurator", "DataManager", "Distributor", "Editor",
    "HostingInstitution", "Producer", "ProjectLeader", "ProjectManager", "ProjectMember",
    "RegistrationAgency", "RegistrationAuthority", "RelatedPerson", "Researcher",
    "ResearchGroup", "RightsHolder", "Supervisor", "Sponsor", "WorkPackageLeader", "Other",
}
RELATIONS = {
    "isCitedBy", "cites", "isSupplementTo", "isSupplementedBy", "isContinuedBy", "continues",
    "isDescribedBy", "describes", "hasMetadata", "isMetadataFor", "isNewVersionOf",
    "isPreviousVersionOf", "isPartOf", "hasPart", "isReferencedBy", "references",
    "isDocumentedBy", "documents", "isCompiledBy", "compiles", "isVariantFormOf",
    "isOriginalFormof", "isIdenticalTo", "isAlternateIdentifier", "isReviewedBy", "reviews",
    "isDerivedFrom", "isSourceOf", "requires", "isRequiredBy", "isObsoletedBy", "obsoletes",
}
ACCESS_RIGHTS = {"open", "embargoed", "restricted", "closed"}


def step(msg):
    print(f"==> {msg}", flush=True)


def note(msg):
    print(f"    {msg}", flush=True)


def read_env(path):
    """Parse simple KEY=VALUE lines. Values are never printed anywhere in this script."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        values[key.strip()] = val
    return values


def get_token(host):
    key = TOKEN_KEYS[host]
    token = read_env(ENV_PATH).get(key) or os.environ.get(key, "")
    if not token.strip():
        raise SystemExit(
            f"Missing {key}. Add the line {key}=<your token> to {ENV_PATH}, creating the token "
            f"at https://{host}/account/settings/applications/tokens/new/ with scopes "
            f"deposit:write and deposit:actions."
        )
    return token.strip()


def parse_body(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace")[:2000]


def fail_http(method, url, exc):
    body = parse_body(exc.read())
    print(f"\nHTTP {exc.code} on {method} {url}", file=sys.stderr)
    if isinstance(body, (dict, list)):
        print(json.dumps(body, indent=2), file=sys.stderr)
    elif body:
        print(body, file=sys.stderr)
    raise SystemExit(f"Zenodo rejected the request ({exc.code}). Nothing was published.")


def api(method, url, token, *, payload=None, body=None, body_len=None, timeout=120, allow=()):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    elif body is not None:
        data = body
        headers["Content-Type"] = "application/octet-stream"
        headers["Content-Length"] = str(body_len)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, parse_body(resp.read())
    except urllib.error.HTTPError as exc:
        if exc.code in allow:
            return exc.code, parse_body(exc.read())
        fail_http(method, url, exc)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error on {method} {url}: {exc.reason}")


def load_doc():
    if not METADATA_PATH.exists():
        raise SystemExit(f"Metadata file not found: {METADATA_PATH}")
    try:
        doc = json.loads(METADATA_PATH.read_text())
    except ValueError as exc:
        raise SystemExit(f"{METADATA_PATH} is not valid JSON: {exc}")
    if not isinstance(doc.get("metadata"), dict):
        raise SystemExit(f"{METADATA_PATH} must have a top-level 'metadata' object.")
    if not isinstance(doc.get("files"), list) or not doc["files"]:
        raise SystemExit(f"{METADATA_PATH} must have a non-empty top-level 'files' array.")
    return doc


def validate_metadata(md):
    errors = []
    for key in ("upload_type", "title", "description", "creators"):
        if not md.get(key):
            errors.append(f"metadata.{key} is required and missing or empty")
    if md.get("upload_type") not in UPLOAD_TYPES:
        errors.append(f"upload_type {md.get('upload_type')!r} is not in the Zenodo vocabulary")
    if md.get("upload_type") == "publication" and md.get("publication_type") not in PUBLICATION_TYPES:
        errors.append(f"publication_type {md.get('publication_type')!r} is required for "
                      "upload_type 'publication' and must be in the Zenodo vocabulary")
    if md.get("access_right", "open") not in ACCESS_RIGHTS:
        errors.append(f"access_right {md.get('access_right')!r} is not in the Zenodo vocabulary")
    if md.get("access_right", "open") in {"open", "embargoed"} and not md.get("license"):
        errors.append("license is required when access_right is open or embargoed")
    for i, person in enumerate(md.get("creators") or []):
        if not isinstance(person, dict) or not person.get("name"):
            errors.append(f"creators[{i}] needs a 'name' in 'Family, Given' form")
    for i, person in enumerate(md.get("contributors") or []):
        if not isinstance(person, dict) or not person.get("name"):
            errors.append(f"contributors[{i}] needs a 'name'")
        elif person.get("type") not in CONTRIBUTOR_TYPES:
            errors.append(f"contributors[{i}].type {person.get('type')!r} is not in the "
                          "Zenodo contributor vocabulary")
    for i, rel in enumerate(md.get("related_identifiers") or []):
        if not isinstance(rel, dict) or not rel.get("identifier"):
            errors.append(f"related_identifiers[{i}] needs an 'identifier'")
        elif rel.get("relation") not in RELATIONS:
            errors.append(f"related_identifiers[{i}].relation {rel.get('relation')!r} is not "
                          "in the Zenodo relation vocabulary")
    if md.get("keywords") is not None and not isinstance(md["keywords"], list):
        errors.append("keywords must be an array of strings")
    date = md.get("publication_date")
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            errors.append(f"publication_date {date!r} must be ISO8601 YYYY-MM-DD")
    return errors


def resolve_files(entries):
    resolved = []
    for entry in entries:
        path = Path(entry["path"])
        if not path.is_absolute():
            path = REPO_ROOT / path
        resolved.append({
            "path": path,
            "name": path.name,
            "required": bool(entry.get("required", True)),
            "exists": path.is_file(),
            "size": path.stat().st_size if path.is_file() else 0,
        })
    return resolved


def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except ValueError:
        raise SystemExit(f"{STATE_PATH} is not valid JSON. Fix or delete it and re-run.")


def save_state(state, host, entry):
    state[host] = entry
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n")
    note(f"state saved: {STATE_PATH} [{host}]")


def state_entry(host, dep, published):
    links = dep.get("links") or {}
    return {
        "host": host,
        "deposition_id": dep.get("id"),
        "record_id": dep.get("record_id"),
        "concept_recid": dep.get("conceptrecid"),
        "doi": dep.get("doi") or (dep.get("metadata") or {}).get("doi") or "",
        "doi_url": dep.get("doi_url", ""),
        "html_url": links.get("html", ""),
        "state": dep.get("state", ""),
        "published": published,
        "version": (dep.get("metadata") or {}).get("version", ""),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def create_deposition(base, token, host, title):
    """Refuse to create a second draft with the same title, which is how duplicates happen."""
    _, listing = api("GET", f"{base}/deposit/depositions?size=100", token, allow=(403,))
    for dep in listing if isinstance(listing, list) else []:
        same_title = ((dep.get("metadata") or {}).get("title") or "") == title
        if same_title and not dep.get("submitted"):
            raise SystemExit(
                f"{host} already has an unsubmitted draft {dep['id']} with this exact title, and "
                f"{STATE_PATH} has no entry for it. Refusing to create a duplicate. Either delete "
                f"that draft at {(dep.get('links') or {}).get('html', host)}, or add "
                f'{{"{host}": {{"deposition_id": {dep["id"]}, "published": false}}}} to '
                f"{STATE_PATH} and re-run."
            )
    _, dep = api("POST", f"{base}/deposit/depositions", token, payload={})
    note(f"created deposition {dep['id']}")
    return dep


def upload_files(base, token, dep_id, bucket, files):
    status, listing = api("GET", f"{base}/deposit/depositions/{dep_id}/files", token)
    existing = {}
    for item in listing or []:
        name = item.get("filename") or item.get("key")
        if name:
            existing[name] = item.get("id")
    for spec in files:
        if not spec["exists"]:
            note(f"skipped (absent): {spec['name']}")
            continue
        if spec["name"] in existing:
            api("DELETE", f"{base}/deposit/depositions/{dep_id}/files/{existing[spec['name']]}",
                token, allow=(404,))
            note(f"removed previous copy of {spec['name']}")
        with spec["path"].open("rb") as fh:
            api("PUT", f"{bucket}/{spec['name']}", token,
                body=fh, body_len=spec["size"], timeout=900)
        note(f"uploaded {spec['name']} ({spec['size'] / 1024:.0f} KB)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="validate metadata and files, touch no network, need no token")
    parser.add_argument("--sandbox", action="store_true",
                        help=f"use {SANDBOX_HOST} and ZENODO_SANDBOX_TOKEN")
    parser.add_argument("--publish", action="store_true",
                        help="publish the deposition and mint the DOI (default is draft only)")
    parser.add_argument("--new-version", action="store_true",
                        help="start a new version of the already published record for this host")
    args = parser.parse_args()

    host = SANDBOX_HOST if args.sandbox else PROD_HOST
    base = f"https://{host}/api"

    step(f"host {host}, mode {'dry-run' if args.dry_run else ('publish' if args.publish else 'draft')}")

    step(f"reading metadata: {METADATA_PATH}")
    doc = load_doc()
    md = doc["metadata"]
    errors = validate_metadata(md)
    if errors:
        for err in errors:
            print(f"    INVALID: {err}", file=sys.stderr)
        raise SystemExit(f"{len(errors)} metadata problem(s). Fix {METADATA_PATH} and re-run.")
    note(f"title: {md['title']}")
    note(f"type: {md['upload_type']}/{md.get('publication_type', '')}, "
         f"license {md.get('license', '')}, version {md.get('version', '')}")
    note(f"creators: {', '.join(c['name'] for c in md['creators'])}")
    note(f"description: {len(md['description'].split())} words as written")
    note("metadata validates against the documented Zenodo vocabularies")

    step("checking files")
    files = resolve_files(doc["files"])
    missing_required = []
    for spec in files:
        if spec["exists"]:
            note(f"OK       {spec['name']}  {spec['size'] / 1024:.0f} KB")
        else:
            label = "REQUIRED" if spec["required"] else "optional"
            note(f"MISSING  {spec['name']}  ({label}, {spec['path']})")
            if spec["required"]:
                missing_required.append(spec)
    present = [s for s in files if s["exists"]]

    if args.dry_run:
        if missing_required:
            note(f"WARNING: {len(missing_required)} required file(s) absent. A real run stops "
                 "here until they exist.")
        state = load_state()
        entry = state.get(host)
        step("deposition state")
        if entry:
            note(f"existing entry for {host}: deposition {entry.get('deposition_id')}, "
                 f"published={entry.get('published')}, doi={entry.get('doi') or 'none'}")
            note("a real run would update that deposition, not create a new one")
        else:
            note(f"no entry for {host} in {STATE_PATH}; a real run would create a new deposition "
                 "after checking the account for a same-titled draft")
        step(f"dry run complete: metadata valid, {len(present)}/{len(files)} files present, "
             "no network calls made")
        return

    if missing_required:
        raise SystemExit(
            f"{len(missing_required)} required file(s) missing: "
            f"{', '.join(s['name'] for s in missing_required)}. Build them or set "
            f"\"required\": false in {METADATA_PATH}, then re-run."
        )

    token = get_token(host)
    note(f"token loaded from {ENV_PATH} as {TOKEN_KEYS[host]}")
    state = load_state()
    entry = state.get(host)

    step("resolving the target deposition")
    if args.new_version:
        if not entry or not entry.get("published"):
            raise SystemExit(f"--new-version needs a published record for {host} in {STATE_PATH}. "
                             "None found. Run without --new-version first.")
        source_id = entry["deposition_id"]
        _, resp = api("POST", f"{base}/deposit/depositions/{source_id}/actions/newversion", token)
        draft_url = (resp.get("links") or {}).get("latest_draft")
        if not draft_url:
            raise SystemExit("Zenodo returned no links.latest_draft for the new version.")
        _, dep = api("GET", draft_url, token)
        note(f"new version drafted from record {source_id}: deposition {dep['id']}")
        note("Zenodo copies the previous version's files into the draft; matching names are "
             "replaced below")
        if entry.get("version") and entry["version"] == md.get("version"):
            note(f"WARNING: metadata version is still {md.get('version')!r}, same as the "
                 "published record. Bump it before publishing.")
    elif entry and entry.get("deposition_id"):
        status, dep = api("GET", f"{base}/deposit/depositions/{entry['deposition_id']}", token,
                          allow=(404, 410))
        if status in (404, 410):
            note(f"deposition {entry['deposition_id']} is gone from {host}; creating a new one")
            dep = create_deposition(base, token, host, md["title"])
        elif dep.get("submitted"):
            raise SystemExit(f"Deposition {dep['id']} on {host} is already published "
                             f"(DOI {dep.get('doi', 'unknown')}). Re-run with --new-version to "
                             "publish an update.")
        else:
            note(f"reusing existing draft {dep['id']}")
    else:
        dep = create_deposition(base, token, host, md["title"])

    dep_id = dep["id"]
    bucket = (dep.get("links") or {}).get("bucket")
    if not bucket:
        raise SystemExit(f"Deposition {dep_id} returned no links.bucket, cannot upload files.")

    step(f"uploading {len(present)} file(s) to deposition {dep_id}")
    upload_files(base, token, dep_id, bucket, files)

    step("writing metadata")
    _, dep = api("PUT", f"{base}/deposit/depositions/{dep_id}", token, payload={"metadata": md})
    note("metadata accepted")

    draft_url = (dep.get("links") or {}).get("html", f"https://{host}/uploads/{dep_id}")
    save_state(state, host, state_entry(host, dep, published=False))

    if not args.publish:
        step("DRAFT ready, nothing is public yet")
        print(f"\n    review it here: {draft_url}")
        print("    publish it with: python experiments/zenodo_upload.py"
              f"{' --sandbox' if args.sandbox else ''} --publish\n")
        return

    step(f"publishing deposition {dep_id} on {host}")
    _, dep = api("POST", f"{base}/deposit/depositions/{dep_id}/actions/publish", token)
    doi = dep.get("doi") or (dep.get("metadata") or {}).get("doi", "")
    record_url = (dep.get("links") or {}).get("record_html") or (dep.get("links") or {}).get("html", "")
    save_state(state, host, state_entry(host, dep, published=True))
    step("PUBLISHED")
    print(f"\n    DOI:    {doi}")
    print(f"    DOI URL: {dep.get('doi_url') or ('https://doi.org/' + doi if doi else '')}")
    print(f"    record: {record_url}\n")


if __name__ == "__main__":
    main()
