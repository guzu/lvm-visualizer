# LVM Segments Visualizer

A "vide-coded" Python tool to visualize the distribution of LVM (Logical Volume Manager) segments across physical disks on Linux systems.

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

# With HTML output
python3 lvm_visualizer.py --html
```

### File Analysis
Analyze from a saved `pvdisplay` output:
```bash
# Create the data file first
sudo pvdisplay -m --units M > my_lvm_data.txt

# Analyze the file
python3 lvm_visualizer.py my_lvm_data.txt
```

## File Format (IMPORTANT)

The tool expects the output of:
```bash
sudo pvdisplay -m --units M
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

## License

This tool is provided as-is for system administration and analysis purposes.
