#!/usr/bin/env python3
import argparse, sys, os, json
from vttfg.orchestrator import Orchestrator

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--jira', required=False, help='JIRA id to process')
    args = p.parse_args()
    orc = Orchestrator()
    jira = args.jira or input('Enter JIRA id: ').strip()
    print('Fetching and running...')
    res = orc.run_for_jira(jira)
    print('Result:', json.dumps(res, indent=2))

if __name__ == '__main__':
    main()
