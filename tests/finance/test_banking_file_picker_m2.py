#!/usr/bin/env python3
"""Banking M2: hostile local CSV selection; no bank/network or disk writes."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
READER=ROOT/"scripts/finance/banking_csv_reader.py"
PREFIX="FINANCEW_BANKING_FILE_RESULT "

def invoke(data: dict | str):
    payload=json.dumps(data,separators=(",",":"))+"\n" if isinstance(data,dict) else data
    result=subprocess.run([sys.executable,str(READER)],input=payload.encode("utf-8"),
        capture_output=True,timeout=6,check=False)
    assert result.stderr==b"",result.stderr
    output=result.stdout.decode("utf-8")
    assert output.count(PREFIX)==1,output[:200]
    assert output.startswith(PREFIX) and output.endswith("\n"),output[:200]
    message=json.loads(output[len(PREFIX):])
    return result.returncode,message,output

def command(url,token="file-1"):
    return {"version":1,"token":token,"fileUrl":url}

with tempfile.TemporaryDirectory(prefix="finance-bank-m2-") as folder:
    base=Path(folder)
    picked=base/"statement 11-22.csv"
    text='Date,Description,Amount\n2026-11-22,"Coffee, Store",-12.50\n'
    picked.write_text(text,encoding="utf-8")
    before=picked.read_bytes()
    url=picked.as_uri()
    code,data,output=invoke(command(url))
    assert code==0 and data=={"version":1,"token":"file-1","ok":True,"csv":text},data
    assert picked.read_bytes()==before,"Read operation changed the source file"
    assert str(picked) not in output,"Picker must not emit paths"
    assert "%20" in url
    code,data,_=invoke(command(url,token="file-22"))
    assert code==0 and data["token"]=="file-22"

    for malformed in (
        command("https://bank.example/statement.csv"),
        command("file://remotehost/tmp/statement.csv"),
        command("file:///tmp/private.csv?version=1"),
        command("file:///tmp/../private.csv"),
        command("file:///tmp/%2E%2E/private.csv"),
        command("file:///tmp/bad%GG.csv"),
        command("file:///tmp/private.txt"),
        command("file:///tmp/%FF.csv"),
        command(url,"wrong-token"),
        {"version":2,"token":"file-1","fileUrl":url},
        {"version":True,"token":"file-1","fileUrl":url},
        {"version":1,"token":"file-1","fileUrl":url,"extra":True},
    ):
        code,data,output=invoke(malformed)
        assert code==2 and data["ok"] is False, (malformed,data)
        assert str(picked) not in output and "Coffee" not in output

    code,data,_=invoke("bad-json\n")
    assert code==2 and data["ok"] is False
    code,data,_=invoke("A"*5000+"\n")
    assert code==2 and data["ok"] is False

    oversized=base/"oversized.csv"
    oversized.write_bytes(b"Date,Description,Amount\n"+b"x"*65536)
    code,data,output=invoke(command(oversized.as_uri()))
    assert code==2 and data["error"]=="FILE_NOT_OWNED_REGULAR_OR_EXCEEDS_64K"
    assert str(oversized) not in output

    empty=base/"empty.csv"
    empty.write_bytes(b"")
    code,data,_=invoke(command(empty.as_uri()))
    assert code==2 and data["ok"] is False

    invalid=base/"nonutf8.csv"
    invalid.write_bytes(b"Date,Description,Amount\n\xff\n")
    code,data,_=invoke(command(invalid.as_uri()))
    assert code==2 and data["error"]=="UTF8_CSV_REQUIRED"

    alias=base/"alias.csv"
    alias.symlink_to(picked)
    code,data,_=invoke(command(alias.as_uri()))
    assert code==2 and data["ok"] is False,"Symlink must not be followed"

    folder_named_csv=base/"directory.csv"
    folder_named_csv.mkdir()
    code,data,_=invoke(command(folder_named_csv.as_uri()))
    assert code==2 and data["ok"] is False

    fifo=base/"pipe.csv"
    os.mkfifo(fifo)
    code,data,_=invoke(command(fifo.as_uri()))
    assert code==2 and data["ok"] is False,"Nonblocking open must not read FIFO"

    newline=base/"newline.csv"
    newline.write_text("Date,Description,Amount\n2026-11-22,a,-1.00\n",encoding="utf-8")
    code,data,_=invoke(command(newline.as_uri()))
    assert code==0 and data["ok"] is True

print("Banking M2: bounded local CSV reader, malicious URLs, symlinks, FIFO, size, UTF-8 and no writes PASS")
