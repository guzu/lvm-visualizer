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
        
    def parse_pvdisplay_output(self, output):
        """Parse pvdisplay -m --units M output"""
        pvs = {}
        current_pv = None
        
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            
            if line.startswith('PV Name'):
                current_pv = line.split()[2]
                pvs[current_pv] = {
                    'vg': '',
                    'size': 0,
                    'free_pe': 0,
                    'total_pe': 0,
                    'segments': []
                }
            elif line.startswith('VG Name') and current_pv:
                pvs[current_pv]['vg'] = line.split()[2]
            elif line.startswith('PV Size') and current_pv:
                size_match = re.search(r'(\d+\.?\d*)', line)
                if size_match:
                    pvs[current_pv]['size'] = float(size_match.group(1))
            elif line.startswith('Free PE') and current_pv:
                pvs[current_pv]['free_pe'] = int(line.split()[2])
            elif line.startswith('Total PE') and current_pv:
                pvs[current_pv]['total_pe'] = int(line.split()[2])
            elif 'Physical extent' in line and current_pv:
                # Parse physical segments
                if 'FREE' in line:
                    # Free segment
                    extent_match = re.search(r'Physical extent (\d+) to (\d+)', line)
                    if extent_match:
                        start, end = int(extent_match.group(1)), int(extent_match.group(2))
                        pvs[current_pv]['segments'].append({
                            'start': start,
                            'end': end,
                            'lv': 'FREE',
                            'size': (end - start + 1) * 4.19  # PE Size in MB
                        })
                else:
                    # Allocated segment
                    extent_match = re.search(r'Physical extent (\d+) to (\d+)', line)
                    if extent_match:
                        start, end = int(extent_match.group(1)), int(extent_match.group(2))
                        # Next line contains the LV
                        continue
            elif line.startswith('Logical volume') and current_pv:
                # Get LV name for the previous segment
                lv_name = line.split()[2].split('/')[-1]
                if pvs[current_pv]['segments']:
                    # Find the last added segment and update the LV
                    for segment in reversed(pvs[current_pv]['segments']):
                        if 'lv' not in segment or segment['lv'] == '':
                            segment['lv'] = lv_name
                            break
        
        return pvs

    def parse_pvdisplay_from_data(self, pvdisplay_content):
        """Parse pvdisplay data provided directly"""
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
                    'pe_size': 4.19,
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
        for pv_name in sorted(pvs.keys()):
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

def main():
    """Main function"""
    analyzer = LVMAnalyzer()
    
    # Your system data (paste complete pvdisplay -m --units M output here)
    pvdisplay_output = """
  --- Physical volume ---
  PV Name               /dev/nvme0n1p3
  VG Name               vg0
  PV Size               510938.58 MB / not usable 0 MB
  Allocatable           yes 
  PE Size               4.19 MB
  Total PE              121817
  Free PE               113625
  Allocated PE          8192
  PV UUID               eLre16-RCs5-1wq8-JlnU-QE2q-saKc-eOtIMp
   
  --- Physical Segments ---
  Physical extent 0 to 8191:
    Logical volume	/dev/vg0/lv-root
    Logical extents	0 to 8191
  Physical extent 8192 to 121816:
    FREE
   
  --- Physical volume ---
  PV Name               /dev/sdd2
  VG Name               purelvm
  PV Size               2000593.30 MB / not usable 2.56 MB
  Allocatable           yes (but full)
  PE Size               4.19 MB
  Total PE              476978
  Free PE               0
  Allocated PE          476978
  PV UUID               RQYuq8-CB1I-u0L4-10lp-I5hr-2wkq-RqL2rl
   
  --- Physical Segments ---
  Physical extent 0 to 204799:
    Logical volume	/dev/purelvm/video
    Logical extents	0 to 204799
  Physical extent 204800 to 239821:
    Logical volume	/dev/purelvm/video
    Logical extents	297778 to 332799
  Physical extent 239822 to 247501:
    Logical volume	/dev/purelvm/netshare
    Logical extents	0 to 7679
  Physical extent 247502 to 298701:
    Logical volume	/dev/purelvm/video
    Logical extents	332800 to 383999
  Physical extent 298702 to 306381:
    Logical volume	/dev/purelvm/photos
    Logical extents	0 to 7679
  Physical extent 306382 to 383999:
    Logical volume	/dev/purelvm/video
    Logical extents	384000 to 461617
  Physical extent 384000 to 476977:
    Logical volume	/dev/purelvm/video
    Logical extents	204800 to 297777
   
  --- Physical volume ---
  PV Name               /dev/sdc1
  VG Name               purelvm
  PV Size               3000591.92 MB / not usable 3.61 MB
  Allocatable           yes 
  PE Size               4.19 MB
  Total PE              715396
  Free PE               170423
  Allocated PE          544973
  PV UUID               8d1cUy-o8eC-YnvS-rG22-BO3j-bS2u-rL4W6J
   
  --- Physical Segments ---
  Physical extent 0 to 249601:
    Logical volume	/dev/purelvm/timemachine
    Logical extents	0 to 249601
  Physical extent 249602 to 300801:
    Logical volume	/dev/purelvm/video
    Logical extents	537600 to 588799
  Physical extent 300802 to 480001:
    Logical volume	/dev/purelvm/bigtmp
    Logical extents	0 to 179199
  Physical extent 480002 to 544972:
    Logical volume	/dev/purelvm/timemachine
    Logical extents	249602 to 314572
  Physical extent 544973 to 715395:
    FREE
   
  --- Physical volume ---
  PV Name               /dev/sda1
  VG Name               purelvm
  PV Size               4000785.96 MB / not usable 2.96 MB
  Allocatable           yes 
  PE Size               4.19 MB
  Total PE              953861
  Free PE               586499
  Allocated PE          367362
  PV UUID               RVgbZk-TUPd-5UWD-d9IH-nwNG-158W-Xc2adJ
   
  --- Physical Segments ---
  Physical extent 0 to 230399:
    Logical volume	/dev/purelvm/archives_rimage_1
    Logical extents	0 to 230399
  Physical extent 230400 to 238079:
    Logical volume	/dev/purelvm/git_rimage_0
    Logical extents	0 to 7679
  Physical extent 238080 to 262861:
    FREE
  Physical extent 262862 to 262862:
    Logical volume	/dev/purelvm/git_rmeta_0
    Logical extents	0 to 0
  Physical extent 262863 to 276479:
    FREE
  Physical extent 276480 to 277759:
    Logical volume	/dev/purelvm/git_rimage_0
    Logical extents	7680 to 8959
  Physical extent 277760 to 277760:
    Logical volume	/dev/purelvm/chloe_rmeta_0
    Logical extents	0 to 0
  Physical extent 277761 to 405760:
    Logical volume	/dev/purelvm/chloe_rimage_0
    Logical extents	0 to 127999
  Physical extent 405761 to 953860:
    FREE
   
  --- Physical volume ---
  PV Name               /dev/sdb
  VG Name               purelvm
  PV Size               4000787.03 MB / not usable 4.02 MB
  Allocatable           yes 
  PE Size               4.19 MB
  Total PE              953861
  Free PE               586498
  Allocated PE          367363
  PV UUID               IqbNRv-C3za-OP9Q-fmiC-nrST-11LF-iqM8tk
   
  --- Physical Segments ---
  Physical extent 0 to 0:
    Logical volume	/dev/purelvm/archives_rmeta_0
    Logical extents	0 to 0
  Physical extent 1 to 230400:
    Logical volume	/dev/purelvm/archives_rimage_0
    Logical extents	0 to 230399
  Physical extent 230401 to 230401:
    Logical volume	/dev/purelvm/git_rmeta_1
    Logical extents	0 to 0
  Physical extent 230402 to 239361:
    Logical volume	/dev/purelvm/git_rimage_1
    Logical extents	0 to 8959
  Physical extent 239362 to 239362:
    Logical volume	/dev/purelvm/chloe_rmeta_1
    Logical extents	0 to 0
  Physical extent 239363 to 367362:
    Logical volume	/dev/purelvm/chloe_rimage_1
    Logical extents	0 to 127999
  Physical extent 367363 to 953860:
    FREE
   
  --- Physical volume ---
  PV Name               /dev/sdd1
  VG Name               purelvm
  PV Size               999998.62 MB / not usable 0 MB
  Allocatable           yes 
  PE Size               4.19 MB
  Total PE              238418
  Free PE               113795
  Allocated PE          124623
  PV UUID               Jhnlvk-e4uU-WzWe-4osd-cNOI-Lc6s-USwrED
   
  --- Physical Segments ---
  Physical extent 0 to 75981:
    Logical volume	/dev/purelvm/video
    Logical extents	461618 to 537599
  Physical extent 75982 to 101581:
    Logical volume	/dev/purelvm/video
    Logical extents	588800 to 614399
  Physical extent 101582 to 111821:
    Logical volume	/dev/purelvm/backup
    Logical extents	0 to 10239
  Physical extent 111822 to 111822:
    Logical volume	/dev/purelvm/archives_rmeta_1
    Logical extents	0 to 0
  Physical extent 111823 to 124622:
    Logical volume	/dev/purelvm/backup
    Logical extents	10240 to 23039
  Physical extent 124623 to 238417:
    FREE
"""

    # Parse data
    try:
        pvs = analyzer.parse_pvdisplay_from_data(pvdisplay_output)
        
        # Display summary
        analyzer.print_summary(pvs)
        
        # Create visualization
        fig = analyzer.create_visualization(pvs)
        
        # Save chart
        plt.savefig('lvm_segments_visualization.png', dpi=300, bbox_inches='tight')
        print(f"\n✅ Chart saved: lvm_segments_visualization.png")
        
        # Display chart
        plt.show()
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()

def run_live_analysis():
    """Run live analysis of LVM commands"""
    print("🔍 Live LVM system analysis...")
    
    try:
        # Execute pvdisplay -m --units M
        result = subprocess.run(['sudo', 'pvdisplay', '-m', '--units', 'M'], 
                              capture_output=True, text=True, check=True)
        
        analyzer = LVMAnalyzer()
        pvs = analyzer.parse_pvdisplay_output(result.stdout)
        
        # Display summary and create visualization
        analyzer.print_summary(pvs)
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
    
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        # Live analysis mode
        run_live_analysis()
    else:
        # Pre-filled data mode
        print("📋 Pre-filled data analysis mode")
        print("💡 Use --live to analyze your system directly")
        main()
