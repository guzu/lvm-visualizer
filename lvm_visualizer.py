#!/usr/bin/env python3
"""
LVM Segments Visualizer for Linux
Analyzes the distribution of logical volumes across physical disks
"""

import re
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import defaultdict, OrderedDict
import subprocess
import sys

class LVMAnalyzer:
    def __init__(self):
        self.pv_data = {}
        self.vg_data = {}
        self.lv_colors = {}
        self.color_palette = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D7BDE2'
        ]

    def parse_pvdisplay(self, pvdisplay_content):
        """Parse pvdisplay -m --units M output (from file or command)"""
        pvs = {}
        current_pv = None
        in_segments = False

        lines = pvdisplay_content.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if line.startswith('PV Name'):
                current_pv = line.split()[2]
                pvs[current_pv] = {
                    'vg': '',
                    'size': 0,
                    'free_pe': 0,
                    'total_pe': 0,
                    'pe_size': 4.19,  # Default PE size, will be updated if found
                    'segments': []
                }
                in_segments = False
            elif line.startswith('VG Name') and current_pv:
                pvs[current_pv]['vg'] = line.split()[2]
            elif line.startswith('PV Size') and current_pv:
                size_match = re.search(r'(\d+\.?\d*)', line)
                if size_match:
                    pvs[current_pv]['size'] = float(size_match.group(1))
            elif line.startswith('PE Size') and current_pv:
                pe_match = re.search(r'(\d+\.?\d*)', line)
                if pe_match:
                    pvs[current_pv]['pe_size'] = float(pe_match.group(1))
            elif line.startswith('Free PE') and current_pv:
                pvs[current_pv]['free_pe'] = int(line.split()[2])
            elif line.startswith('Total PE') and current_pv:
                pvs[current_pv]['total_pe'] = int(line.split()[2])
            elif line.startswith('--- Physical Segments ---'):
                in_segments = True
            elif in_segments and 'Physical extent' in line and current_pv:
                # Parse physical segments
                extent_match = re.search(r'Physical extent (\d+) to (\d+)', line)
                if extent_match:
                    start, end = int(extent_match.group(1)), int(extent_match.group(2))

                    # Check next line for LV
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if 'FREE' in next_line:
                            lv_name = 'FREE'
                        elif 'Logical volume' in next_line:
                            lv_name = next_line.split()[2].split('/')[-1]
                        else:
                            lv_name = 'UNKNOWN'
                    else:
                        lv_name = 'FREE'

                    segment_size = (end - start + 1) * pvs[current_pv]['pe_size']
                    pvs[current_pv]['segments'].append({
                        'start': start,
                        'end': end,
                        'lv': lv_name,
                        'size': segment_size
                    })
            i += 1

        return pvs

    def assign_colors(self, pvs):
        """Assign unique colors to each LV"""
        all_lvs = set()
        for pv_data in pvs.values():
            for segment in pv_data['segments']:
                all_lvs.add(segment['lv'])

        color_idx = 0
        for lv in sorted(all_lvs):
            if lv == 'FREE':
                self.lv_colors[lv] = '#E8E8E8'  # Light gray for free space
            else:
                self.lv_colors[lv] = self.color_palette[color_idx % len(self.color_palette)]
                color_idx += 1

    def create_visualization(self, pvs):
        """Create visualizations"""
        self.assign_colors(pvs)

        # Chart configuration
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))
        fig.suptitle('LVM Segments Distribution by Physical Disk', fontsize=16, fontweight='bold')

        # Chart 1: PV overview
        self.plot_pv_overview(ax1, pvs)

        # Chart 2: Segments detail
        self.plot_segments_detail(ax2, pvs)

        plt.tight_layout()
        return fig

    def plot_pv_overview(self, ax, pvs):
        """Stacked bar chart by PV"""
        # Sort PVs by name
        pv_names = sorted(list(pvs.keys()))
        lv_usage = defaultdict(list)

        # Calculate usage by LV on each PV
        for pv_name in pv_names:
            lv_sizes = defaultdict(float)
            for segment in pvs[pv_name]['segments']:
                lv_sizes[segment['lv']] += segment['size']

            # Add each LV
            all_lvs = set()
            for pv_data in pvs.values():
                for segment in pv_data['segments']:
                    all_lvs.add(segment['lv'])

            for lv in sorted(all_lvs):
                lv_usage[lv].append(lv_sizes.get(lv, 0))

        # Create stacked bars
        x = np.arange(len(pv_names))
        width = 0.6
        bottom = np.zeros(len(pv_names))

        for lv in sorted(lv_usage.keys()):
            if lv != 'FREE':  # Handle FREE separately
                values = lv_usage[lv]
                ax.bar(x, values, width, label=lv, bottom=bottom,
                       color=self.lv_colors[lv], alpha=0.8)
                bottom += values

        # Add free space last
        if 'FREE' in lv_usage:
            ax.bar(x, lv_usage['FREE'], width, label='Free Space',
                   bottom=bottom, color=self.lv_colors['FREE'], alpha=0.6)

        ax.set_xlabel('Physical Volumes')
        ax.set_ylabel('Size (MB)')
        ax.set_title('Space Usage by PV')
        ax.set_xticks(x)
        ax.set_xticklabels([pv.split('/')[-1] for pv in pv_names], rotation=45)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)

    def plot_segments_detail(self, ax, pvs):
        """Detailed segments chart by PV"""
        y_pos = 0
        y_labels = []
        y_positions = []

        # Sort PVs by name
        for pv_name in reversed(sorted(pvs.keys())):
            pv_data = pvs[pv_name]
            y_labels.append(pv_name.split('/')[-1])
            y_positions.append(y_pos)

            # Sort segments by position
            sorted_segments = sorted(pv_data['segments'], key=lambda x: x['start'])

            current_pos = 0
            for segment in sorted_segments:
                size_gb = segment['size'] / 1024  # Convert to GB for readability
                ax.barh(y_pos, size_gb, left=current_pos,
                       color=self.lv_colors[segment['lv']],
                       alpha=0.8, edgecolor='white', linewidth=0.5)

                # Add LV name if segment is large enough
                if size_gb > 10:  # Only if larger than 10GB
                    ax.text(current_pos + size_gb/2, y_pos, segment['lv'],
                           ha='center', va='center', fontsize=8,
                           fontweight='bold' if segment['lv'] != 'FREE' else 'normal')

                current_pos += size_gb

            y_pos += 1

        ax.set_xlabel('Size (GB)')
        ax.set_ylabel('Physical Volumes')
        ax.set_title('Detailed Segments Distribution')
        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels)
        ax.grid(True, alpha=0.3, axis='x')

    def create_html_visualization(self, pvs, output_file="lvm_visualization.html"):
        """Create HTML visualization with D3.js"""
        import json
        self.assign_colors(pvs)

        # Prepare data for JavaScript
        pv_names = sorted(list(pvs.keys()))

        # Data for PV overview chart
        overview_data = []
        for pv_name in pv_names:
            pv_data = pvs[pv_name]
            lv_sizes = defaultdict(float)

            for segment in pv_data['segments']:
                lv_sizes[segment['lv']] += segment['size']

            pv_entry = {
                'pv': pv_name.split('/')[-1],
                'total_size': pv_data['size'],
                'segments': []
            }

            for lv in sorted(lv_sizes.keys()):
                pv_entry['segments'].append({
                    'lv': lv,
                    'size': lv_sizes[lv],
                    'color': self.lv_colors[lv]
                })

            overview_data.append(pv_entry)

        # Data for segments detail chart
        segments_data = []
        for pv_name in reversed(sorted(pvs.keys())):
            pv_data = pvs[pv_name]
            sorted_segments = sorted(pv_data['segments'], key=lambda x: x['start'])

            pv_segments = {
                'pv': pv_name.split('/')[-1],
                'segments': []
            }

            for segment in sorted_segments:
                pv_segments['segments'].append({
                    'lv': segment['lv'],
                    'size': segment['size'] / 1024,  # Convert to GB
                    'color': self.lv_colors[segment['lv']]
                })

            segments_data.append(pv_segments)

        # Create HTML template
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LVM Segments Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
            font-size: 2.5em;
        }}
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .tooltip {{
            position: absolute;
            text-align: center;
            padding: 8px 12px;
            font-size: 12px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            border-radius: 6px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            margin: 20px 0;
            gap: 15px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }}
        .axis {{
            font-size: 12px;
        }}
        .axis-label {{
            font-size: 14px;
            font-weight: bold;
            fill: #333;
        }}
        .grid line {{
            stroke: #e0e0e0;
            stroke-opacity: 0.7;
        }}
        .grid path {{
            stroke-width: 0;
        }}
        .bar:hover {{
            opacity: 0.8;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 LVM Segments Distribution by Physical Disk</h1>

        <div class="chart-container">
            <h2>Space Usage by PV</h2>
            <div id="overview-chart"></div>
        </div>

        <div class="chart-container">
            <h2>Detailed Segments Distribution</h2>
            <div id="segments-chart"></div>
        </div>

        <div id="legend" class="legend"></div>
    </div>

    <div class="tooltip" id="tooltip"></div>

    <script>
        // Data
        const overviewData = {json.dumps(overview_data)};
        const segmentsData = {json.dumps(segments_data)};

        // Get all unique LVs for legend
        const allLVs = new Set();
        const lvColors = {{}};

        overviewData.forEach(pv => {{
            pv.segments.forEach(segment => {{
                allLVs.add(segment.lv);
                lvColors[segment.lv] = segment.color;
            }});
        }});

        // Create legend
        const legend = d3.select("#legend");
        Array.from(allLVs).sort().forEach(lv => {{
            const item = legend.append("div").attr("class", "legend-item");
            item.append("div")
                .attr("class", "legend-color")
                .style("background-color", lvColors[lv]);
            item.append("span").text(lv);
        }});

        // Tooltip
        const tooltip = d3.select("#tooltip");

        // Overview Chart (Stacked Bar)
        function createOverviewChart() {{
            const margin = {{top: 20, right: 20, bottom: 80, left: 80}};
            const width = 800 - margin.left - margin.right;
            const height = 400 - margin.top - margin.bottom;

            const svg = d3.select("#overview-chart")
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom);

            const g = svg.append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            // Scales
            const xScale = d3.scaleBand()
                .domain(overviewData.map(d => d.pv))
                .range([0, width])
                .padding(0.2);

            const yScale = d3.scaleLinear()
                .domain([0, d3.max(overviewData, d => d.total_size)])
                .range([height, 0]);

            // Stack data
            const stackedData = overviewData.map(pv => {{
                let cumulative = 0;
                const segments = pv.segments.map(segment => {{
                    const result = {{
                        lv: segment.lv,
                        size: segment.size,
                        color: segment.color,
                        y0: cumulative,
                        y1: cumulative + segment.size,
                        pv: pv.pv
                    }};
                    cumulative += segment.size;
                    return result;
                }});
                return {{ pv: pv.pv, segments, total: pv.total_size }};
            }});

            // Draw bars
            stackedData.forEach(pvData => {{
                const pvGroup = g.append("g");

                pvData.segments.forEach(segment => {{
                    pvGroup.append("rect")
                        .attr("class", "bar")
                        .attr("x", xScale(pvData.pv))
                        .attr("y", yScale(segment.y1))
                        .attr("width", xScale.bandwidth())
                        .attr("height", yScale(segment.y0) - yScale(segment.y1))
                        .attr("fill", segment.color)
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 1)
                        .on("mouseover", function(event) {{
                            tooltip.style("opacity", 1)
                                .html(`<strong>${{segment.lv}}</strong><br/>
                                      PV: ${{pvData.pv}}<br/>
                                      Size: ${{(segment.size/1024).toFixed(1)}} GB<br/>
                                      (${{segment.size.toFixed(0)}} MB)`)
                                .style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 10) + "px");
                        }})
                        .on("mouseout", function() {{
                            tooltip.style("opacity", 0);
                        }});
                }});
            }});

            // Axes
            g.append("g")
                .attr("class", "axis")
                .attr("transform", `translate(0,${{height}})`)
                .call(d3.axisBottom(xScale))
                .selectAll("text")
                .style("text-anchor", "end")
                .attr("dx", "-.8em")
                .attr("dy", ".15em")
                .attr("transform", "rotate(-45)");

            g.append("g")
                .attr("class", "axis")
                .call(d3.axisLeft(yScale));


            // Labels
            g.append("text")
                .attr("class", "axis-label")
                .attr("transform", "rotate(-90)")
                .attr("y", 0 - margin.left)
                .attr("x", 0 - (height / 2))
                .attr("dy", "1em")
                .style("text-anchor", "middle")
                .text("Size (MB)");

            g.append("text")
                .attr("class", "axis-label")
                .attr("transform", `translate(${{width / 2}}, ${{height + margin.bottom - 10}})`)
                .style("text-anchor", "middle")
                .text("Physical Volumes");
        }}

        // Segments Chart (Horizontal Stacked)
        function createSegmentsChart() {{
            const margin = {{top: 20, right: 20, bottom: 60, left: 120}};
            const width = 800 - margin.left - margin.right;
            const height = segmentsData.length * 60 + margin.top + margin.bottom;

            const svg = d3.select("#segments-chart")
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height);

            const g = svg.append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            // Scales
            const maxSize = d3.max(segmentsData, d => d3.sum(d.segments, s => s.size));

            const xScale = d3.scaleLinear()
                .domain([0, maxSize])
                .range([0, width]);

            const yScale = d3.scaleBand()
                .domain(segmentsData.map(d => d.pv))
                .range([0, height - margin.top - margin.bottom])
                .padding(0.2);

            // Draw segments
            segmentsData.forEach(pvData => {{
                let currentX = 0;
                const pvGroup = g.append("g");

                pvData.segments.forEach(segment => {{
                    const segmentWidth = xScale(segment.size);

                    pvGroup.append("rect")
                        .attr("class", "bar")
                        .attr("x", currentX)
                        .attr("y", yScale(pvData.pv))
                        .attr("width", segmentWidth)
                        .attr("height", yScale.bandwidth())
                        .attr("fill", segment.color)
                        .attr("stroke", "#fff")
                        .attr("stroke-width", 1)
                        .on("mouseover", function(event) {{
                            tooltip.style("opacity", 1)
                                .html(`<strong>${{segment.lv}}</strong><br/>
                                      PV: ${{pvData.pv}}<br/>
                                      Size: ${{segment.size.toFixed(1)}} GB`)
                                .style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 10) + "px");
                        }})
                        .on("mouseout", function() {{
                            tooltip.style("opacity", 0);
                        }});

                    // Add text label if segment is large enough
                    if (segmentWidth > 50) {{
                        pvGroup.append("text")
                            .attr("x", currentX + segmentWidth / 2)
                            .attr("y", yScale(pvData.pv) + yScale.bandwidth() / 2)
                            .attr("dy", ".35em")
                            .style("text-anchor", "middle")
                            .style("fill", segment.lv === 'FREE' ? '#666' : 'white')
                            .style("font-size", "12px")
                            .style("font-weight", segment.lv === 'FREE' ? 'normal' : 'bold')
                            .text(segment.lv);
                    }}

                    currentX += segmentWidth;
                }});
            }});

            // Axes
            g.append("g")
                .attr("class", "axis")
                .attr("transform", `translate(0,${{height - margin.top - margin.bottom}})`)
                .call(d3.axisBottom(xScale));

            g.append("g")
                .attr("class", "axis")
                .call(d3.axisLeft(yScale));


            // Labels
            g.append("text")
                .attr("class", "axis-label")
                .attr("transform", `translate(${{width / 2}}, ${{height - margin.bottom + 40}})`)
                .style("text-anchor", "middle")
                .text("Size (GB)");

            g.append("text")
                .attr("class", "axis-label")
                .attr("transform", "rotate(-90)")
                .attr("y", 0 - margin.left)
                .attr("x", 0 - (height / 2))
                .attr("dy", "1em")
                .style("text-anchor", "middle")
                .text("Physical Volumes");
        }}

        // Create both charts
        createOverviewChart();
        createSegmentsChart();
    </script>
</body>
</html>"""

        # Write HTML file
        with open(output_file, 'w') as f:
            f.write(html_template)

        return output_file

    def print_summary(self, pvs):
        """Print text summary"""
        print("\n" + "="*80)
        print("LVM CONFIGURATION SUMMARY")
        print("="*80)

        total_size = 0
        total_used = 0
        total_free = 0

        # Sort PVs by name for consistent output
        for pv_name in sorted(pvs.keys()):
            pv_data = pvs[pv_name]
            print(f"\n💽 {pv_name} (VG: {pv_data['vg']})")
            print(f"   Total size:  {pv_data['size']:>8.1f} MB ({pv_data['size']/1024:.1f} GB)")

            used_size = sum(s['size'] for s in pv_data['segments'] if s['lv'] != 'FREE')
            free_size = sum(s['size'] for s in pv_data['segments'] if s['lv'] == 'FREE')

            print(f"   Used space:  {used_size:>8.1f} MB ({used_size/1024:.1f} GB)")
            print(f"   Free space:  {free_size:>8.1f} MB ({free_size/1024:.1f} GB)")
            print(f"   Usage:       {(used_size/pv_data['size']*100):>6.1f}%")

            # LV details on this PV
            lv_usage = defaultdict(float)
            for segment in pv_data['segments']:
                if segment['lv'] != 'FREE':
                    lv_usage[segment['lv']] += segment['size']

            if lv_usage:
                print("   Logical Volumes:")
                for lv in sorted(lv_usage.keys()):
                    size = lv_usage[lv]
                    print(f"     • {lv:<15} {size:>8.1f} MB ({size/1024:>5.1f} GB)")

            total_size += pv_data['size']
            total_used += used_size
            total_free += free_size

        print(f"\n📊 GLOBAL TOTALS:")
        print(f"   Total capacity: {total_size:>8.1f} MB ({total_size/1024:.1f} GB)")
        print(f"   Used space:     {total_used:>8.1f} MB ({total_used/1024:.1f} GB)")
        print(f"   Free space:     {total_free:>8.1f} MB ({total_free/1024:.1f} GB)")
        print(f"   Usage:          {(total_used/total_size*100):>6.1f}%")

def analyze_from_file(file_path, html_mode=False):
    """Analyze LVM data from file"""
    analyzer = LVMAnalyzer()

    try:
        with open(file_path, 'r') as f:
            pvdisplay_output = f.read()

        # Parse data
        pvs = analyzer.parse_pvdisplay(pvdisplay_output)

        # Display summary
        analyzer.print_summary(pvs)

        if html_mode:
            # Create HTML visualization
            base_filename = file_path.replace(".", "_").replace("/", "_")
            output_filename = f'lvm_segments_{base_filename}.html'
            analyzer.create_html_visualization(pvs, output_filename)
            print(f"\n✅ HTML visualization saved: {output_filename}")
            print("🌐 Open the HTML file in your browser to view the interactive charts")
        else:
            # Create matplotlib visualization
            fig = analyzer.create_visualization(pvs)

            # Save chart
            output_filename = f'lvm_segments_{file_path.replace(".", "_").replace("/", "_")}.png'
            plt.savefig(output_filename, dpi=300, bbox_inches='tight')
            print(f"\n✅ Chart saved: {output_filename}")

            # Display chart
            plt.show()

    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        print("💡 Make sure the file path is correct")
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()

def run_live_analysis(html_mode=False):
    """Run live analysis of LVM commands"""
    print("🔍 Live LVM system analysis...")

    try:
        # Execute pvdisplay -m --units M
        result = subprocess.run(['sudo', 'pvdisplay', '-m', '--units', 'M'],
                                capture_output=True, text=True, check=True)

        analyzer = LVMAnalyzer()
        pvs = analyzer.parse_pvdisplay(result.stdout)

        # Display summary and create visualization
        analyzer.print_summary(pvs)

        if html_mode:
            # Create HTML visualization
            analyzer.create_html_visualization(pvs, 'lvm_segments_live.html')
            print(f"\n✅ Live analysis completed. HTML visualization saved: lvm_segments_live.html")
            print("🌐 Open the HTML file in your browser to view the interactive charts")
        else:
            # Create matplotlib visualization
            fig = analyzer.create_visualization(pvs)
            plt.savefig('lvm_segments_live.png', dpi=300, bbox_inches='tight')
            print(f"\n✅ Live analysis completed. Chart saved: lvm_segments_live.png")
            plt.show()

    except subprocess.CalledProcessError as e:
        print(f"❌ Command execution error: {e}")
        print("💡 Make sure you have sudo rights to execute pvdisplay")
    except FileNotFoundError:
        print("❌ pvdisplay not found. Make sure LVM is installed.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 LVM Segments Visualizer")
    print("-" * 40)

    # Parse arguments
    args = sys.argv[1:]
    html_mode = "--html" in args
    if html_mode:
        args = [arg for arg in args if arg != "--html"]

    if len(args) > 0:
        arg = args[0]
        if arg == "--help":
            # Help
            print("Usage:")
            print("  python3 lvm_visualizer.py [--help] [--html] [file.txt]")
            print("\nFile format: Output of 'sudo pvdisplay -m --units M'")
        else:
            # File analysis mode
            print(f"📄 File analysis mode: {arg}")
            analyze_from_file(arg, html_mode)
    else:
        # Default: Live analysis mode (or HTML mode if --html was specified)
        if html_mode:
            print("🔍 Live system analysis mode with HTML output")
        else:
            print("🔍 Live system analysis mode (default)")
            print("💡 Use 'python3 lvm_visualizer.py <file.txt>' to analyze from file")
        run_live_analysis(html_mode)
