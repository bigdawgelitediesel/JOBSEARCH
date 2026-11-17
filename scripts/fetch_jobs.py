"""Pull live postings from the Laramie County school district job boards and
write jobs.json with the certified general-ed elementary teaching jobs only.
Runs daily from GitHub Actions. No dependencies beyond the standard library."""
import json, re, sys, urllib.request, datetime, pathlib

BOARDS = [
    ("laramie1.schoolspring.com", "Laramie County School District 1 (Cheyenne)"),
    ("laramie2.schoolspring.com", "Laramie County School District 2 (Pine Bluffs / Burns)"),
]
API = ("https://api.schoolspring.com/api/Jobs/GetPagedJobsWithSearch?domainName={d}"
       "&keyword=&location=&category=&gradelevel=&jobtype=&organization="
       "&swLat=&swLon=&neLat=&neLon=&page=1&size=200&sortDateAscending=false")

# must look like a classroom teaching job
TEACHER = re.compile(r"\b(teacher|kindergarten|1st grade|2nd grade|3rd grade|4th grade|5th grade|6th grade|"
                     r"first grade|second grade|third grade|fourth grade|fifth grade|sixth grade|"
                     r"title (one|i)\b|elementary classroom)", re.I)
# and must be elementary
ELEM = re.compile(r"\b(elementary|kindergarten|k-6|k–6|k6|[1-6](st|nd|rd|th) grade|"
                  r"(first|second|third|fourth|fifth|sixth) grade|title (one|i)\b)", re.I)
# and must not be any of these
EXCLUDE = re.compile(r"\b(para|paraeducator|paraprofessional|substitute|\bsub\b|coach|sped|special ed|"
                     r"resource teacher|resource room|dli|dual language|immersion|spanish|speech|interpreter|"
                     r"custod|nutrition|secretary|sweeper|psycholog|therap|nurse|music|art teacher|"
                     r"physical education|\bpe\b|librar|counselor|principal|director|coordinator|"
                     r"life skills|affective|behavior)", re.I)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def main():
    out, seen = [], set()
    for domain, district in BOARDS:
        try:
            jobs = fetch(API.format(d=domain))["value"]["jobsList"]
        except Exception as e:
            print(f"WARN {domain}: {e}", file=sys.stderr); continue
        for j in jobs:
            title, emp = j["title"].strip(), (j.get("employer") or "").strip()
            blob = f"{title} | {emp}"
            if not TEACHER.search(title): continue
            if EXCLUDE.search(blob): continue
            if not ELEM.search(blob): continue
            if j["jobId"] in seen: continue
            seen.add(j["jobId"])
            out.append({
                "id": j["jobId"], "title": title, "school": emp.title().replace("Poder", "PODER").replace("Lcsd", "LCSD"),
                "district": district, "posted": j["displayDate"][:10],
                "url": f"https://{domain}/?jobid={j['jobId']}",
            })
        print(f"{domain}: {len(jobs)} postings scanned", file=sys.stderr)
    out.sort(key=lambda x: x["posted"], reverse=True)
    data = {"updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "jobs": out}
    pathlib.Path("jobs.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"kept {len(out)} elementary teaching jobs", file=sys.stderr)
    for j in out: print(f"  {j['posted']}  {j['school']}: {j['title']}", file=sys.stderr)

if __name__ == "__main__":
    main()
