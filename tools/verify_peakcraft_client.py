"""Record a read-only, private proof of the isolated PeakCraft MC guest load."""

import hashlib
import json
from pathlib import Path

from prepare_peakcraft_profile import ROOT, TARGET, sha


def main():
    report_path = ROOT/'artifacts/peakcraft/profile-plan.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    if not report.get('installed') or Path(report['target']) != TARGET:
        raise ValueError('installed isolated profile proof required')
    if not (TARGET/'MCDN_PEAKCRAFT_BASE').is_file():
        raise ValueError('PeakCraft profile marker missing')
    for name, expected in report['files'].items():
        if name == 'options.txt':
            # Minecraft rewrites line endings when it saves settings on exit.
            staged = (Path(report['stage'])/name).read_text(encoding='utf-8').splitlines()
            installed = (TARGET/name).read_text(encoding='utf-8').splitlines()
            if sorted(staged) != sorted(installed):
                raise ValueError('installed profile options changed')
            continue
        if sha(TARGET/name) != expected:
            raise ValueError(f'installed profile changed: {name}')
    log_path = TARGET/'logs/latest.log'
    raw = log_path.read_bytes()
    log = raw.decode('utf-8', errors='replace')
    required = ('skycraft 0.1.2', 'SkyCraft: digging into Skyrim registered',
                'Created window using SDL video driver: windows',
                "SkyCraft: can't open Skyrim's shared memory yet", 'Stopping!')
    if any(item not in log for item in required):
        raise ValueError('incomplete MC guest load/wait/normal-exit proof')
    if 'Crash report saved to:' in log:
        raise ValueError('MC guest crashed')
    proof = {
        'kind': 'peakcraft-mc-guest-real-client-proof',
        'profile': TARGET.name,
        'logSha256': hashlib.sha256(raw).hexdigest(),
        'logBytes': len(raw),
        'loadedMod': 'skycraft 0.1.2',
        'nativeWindowCreated': True,
        'hostMappingAbsentAtStartup': True,
        'normalMenuExit': True,
        'dcHostConnected': False,
        'productionModeGranted': False,
    }
    out = ROOT/'artifacts/peakcraft/client-load.json'
    out.write_text(json.dumps(proof, indent=2), encoding='utf-8')
    report['realClientLoaded'] = True
    report['clientLoadLogSha256'] = proof['logSha256']
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('PEAKCRAFT_MC_CLIENT_PASS', json.dumps(proof))


if __name__ == '__main__':
    main()

