#!/usr/bin/env python3
import os

import uvicorn


def main():
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
