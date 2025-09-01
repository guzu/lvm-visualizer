# LVM Segments Visualizer

A Python tool to visualize the distribution of LVM (Logical Volume Manager) segments across physical disks on Linux systems.

## Features

- **Live System Analysis**: Direct analysis of your LVM configuration
- **File-based Analysis**: Analyze saved `pvdisplay` output from any system
- **Dual Visualization**: 
  - Stacked bar chart showing space usage by Physical Volume
  - Detailed linear representation of segment distribution
- **RAID Support**: Properly handles RAID1 volumes (_rimage_ and _rmeta_ components)
- **Sorted Display**: Physical Volumes sorted alphabetically for easy reference
- **Comprehensive Summary**: Text-based usage statistics

## Requirements

```bash
pip3 install matplotlib numpy
```

## Usage

### Live Analysis (Default)
Analyze your current system directly:
```bash
# Default mode - analyzes current system
python3 lvm_visualizer.py

# Explicit live mode
python3 lvm_visualizer.py --live
```

### File Analysis
Analyze from a saved `pvdisplay` output:
```bash
# Create the data file first
sudo pvdisplay -m --units M > my_lvm_data.txt

# Analyze the file
python3 lvm_visualizer.py my_lvm_data.txt
```

### Help
```bash
python3 lvm_visualizer.py --help
```

Available options:
- Default (no args): Live system analysis
- `--live`: Explicit live analysis
- `<file.txt>`: Analyze from file
- `--help`: Show help information

## File Format

The tool expects the output of:
```bash
sudo pvdisplay -m --units M
```

This command shows:
- Physical Volume information
- Physical Extent allocation details
- Logical Volume mappings
- Free space segments

## Output

The tool generates:

1. **Text Summary**: Console output showing:
   - Usage statistics per Physical Volume
   - Logical Volume distribution
   - Global capacity overview

2. **Visualization Charts**: PNG file with:
   - Stacked bar chart: Space usage by PV
   - Segment detail chart: Linear representation of physical segments

3. **Chart File**: Saved as `lvm_segments_[filename].png` or `lvm_segments_live.png`

## Example Output

```
💽 /dev/nvme0n1p3 (VG: vg0)
   Total size:   510938.6 MB (498.8 GB)
   Used space:    34359.7 MB (33.6 GB)
   Free space:   476578.8 MB (465.2 GB)
   Usage:          6.9%
   Logical Volumes:
     • lv-root           34359.7 MB ( 33.6 GB)

💽 /dev/sda1 (VG: purelvm)
   Total size:  4000786.0 MB (3906.0 GB)
   Used space:  1540827.9 MB (1505.0 GB)
   Free space:  2459958.1 MB (2401.0 GB)
   Usage:         38.5%
   ...
```

## Troubleshooting

### Permission Issues
For live analysis, you need sudo privileges:
```bash
sudo python3 lvm_visualizer.py
```

### Missing pvdisplay
Install LVM tools:
```bash
# Ubuntu/Debian
sudo apt-get install lvm2

# RHEL/CentOS
sudo yum install lvm2
```

### Dependencies
Install Python dependencies:
```bash
pip3 install matplotlib numpy
```

## Understanding the Visualization

- **Colors**: Each Logical Volume gets a unique color
- **Gray segments**: Free space on Physical Volumes
- **RAID volumes**: Shows _rimage_0/1 (data) and _rmeta_0/1 (metadata) components
- **Fragmentation**: Multiple segments of the same LV show fragmentation across disks

## License

This tool is provided as-is for system administration and analysis purposes.
