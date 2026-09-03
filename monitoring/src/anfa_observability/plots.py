from __future__ import annotations

import argparse
import csv
from pathlib import Path


COLORS=("#2563eb","#dc2626","#16a34a","#9333ea","#ea580c")


def number(value):
    try:return float(value) if value not in ("",None) else None
    except ValueError:return None


def svg_plot(rows:list[dict],series:list[tuple[str,str]],title:str,y_label:str,path:Path)->None:
    width,height=1200,440;left,right,top,bottom=80,25,45,60;plot_w=width-left-right;plot_h=height-top-bottom
    values=[number(row.get(field)) for row in rows for field,_ in series];values=[v for v in values if v is not None]
    ymax=max(values) if values else 1;ymax=ymax*1.1 if ymax>0 else 1;xmax=max(len(rows)-1,1)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">','<rect width="100%" height="100%" fill="white"/>',f'<text x="{width/2}" y="26" text-anchor="middle" font-family="sans-serif" font-size="18">{title}</text>',f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="#111"/>',f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="#111"/>']
    for tick in range(6):
        y=top+plot_h-tick*plot_h/5;value=ymax*tick/5;parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_w}" y2="{y:.1f}" stroke="#e5e7eb"/><text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="sans-serif" font-size="11">{value:.2f}</text>')
    for index,(field,label) in enumerate(series):
        points=[]
        for x,row in enumerate(rows):
            value=number(row.get(field))
            if value is not None:points.append(f'{left+x/xmax*plot_w:.1f},{top+plot_h-value/ymax*plot_h:.1f}')
        if points:parts.append(f'<polyline fill="none" stroke="{COLORS[index%len(COLORS)]}" stroke-width="2" points="{" ".join(points)}"/>')
        lx=left+index*210;parts.append(f'<line x1="{lx}" y1="{height-18}" x2="{lx+24}" y2="{height-18}" stroke="{COLORS[index%len(COLORS)]}" stroke-width="3"/><text x="{lx+30}" y="{height-14}" font-family="sans-serif" font-size="12">{label}</text>')
    parts.extend([f'<text x="{width/2}" y="{height-35}" text-anchor="middle" font-family="sans-serif" font-size="12">seconds from T0</text>',f'<text transform="translate(18 {height/2}) rotate(-90)" text-anchor="middle" font-family="sans-serif" font-size="12">{y_label}</text>','</svg>'])
    path.write_text("".join(parts),encoding="utf-8")


def generate(timeline_path:str,output_directory:str)->list[str]:
    with Path(timeline_path).open(newline="",encoding="utf-8-sig") as handle:rows=list(csv.DictReader(handle))
    output=Path(output_directory);output.mkdir(parents=True,exist_ok=True)
    specifications=[
        ("workload-throughput.svg",[("target_rps","target RPS"),("dispatched_requests","dispatched"),("completed_requests","completed")],"Workload and request outcomes","requests/s"),
        ("replicas-readiness.svg",[("commanded_replicas","controller command"),("deployment_desired_replicas","Deployment desired"),("pod_ready_count","Ready Pods"),("service_ready_endpoints","serving endpoints")],"Replica command and serving readiness","replicas/endpoints"),
        ("latency-errors.svg",[("latency_p99_ms","P99 latency"),("failed_requests","failed"),("timeouts","timeouts")],"Latency and failures","milliseconds / count"),
        ("resources.svg",[("pod_cpu_cores","CPU cores"),("cpu_throttling_ratio","throttling ratio")],"Pod CPU and throttling","cores / ratio"),
    ]
    paths=[]
    for filename,series,title,label in specifications:path=output/filename;svg_plot(rows,series,title,label,path);paths.append(str(path))
    return paths


def main()->None:
    parser=argparse.ArgumentParser(description="Generate dependency-free SVG run plots");parser.add_argument("--timeline",required=True);parser.add_argument("--output-directory",required=True);args=parser.parse_args();print("\n".join(generate(args.timeline,args.output_directory)))


if __name__=="__main__":main()
