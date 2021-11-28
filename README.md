# Description
Extracts `PACKAGE_PIN` information into a text table from an implemented firmware design in a Vivado project using `report_package_pins.tcl` script.  
Produces summary latex tables using `analyze_report.py` and text table.

# Example table outputs

Example text table from `report_package_pins.tcl`
![](README_figure/report_package_pins.txt.png)

Example latex tables from `analyze_report.py`

- `table_pin_count_by_type.tex`  
![](README_figure/table_pin_count_by_type.pdf)
- `table_io_pin_count_by_bank.tex`  
![](README_figure/table_io_pin_count_by_bank.pdf)
- `table_port_with_no_net.tex`  
![](README_figure/table_port_with_no_net.pdf)

# Running scripts
## Running `report_package_pins.tcl` script
There are two methods of running `report_package_pins.tcl` script

### Method 1: Run tcl script in Vivado batch mode with arguments

`vivado -nojournal -nolog -mode batch -source report_package_pins.tcl -tclargs PATH_TO_PROJECT.xpr DESIGN_NAME OUTPUT_FILENAME`

`DESIGN_NAME` is implemented design name in Vivado and `OUTPUT_FILENAME` is file that has text table

Example: `vivado -mode batch -source report_package_pins.tcl -tclargs project.xpr impl_1 report_package_pins.txt`

### Method 2: Run tcl script in Vivado tcl mode with arguments

`vivado -mode tcl`  
`set argc 3`  
`set argv [list PATH_TO_PROJECT.xpr DESIGN_NAME OUTPUT_FILENAME]`  
`source report_package_pins.tcl`

## Running `analyze_report.py` script

`analyze_report.py --input_report_filename REPORT_FILENAME`  

`REPORT_FILENAME` is output filename of `report_package_pins.tcl`.

Example: `analyze_report.py --input_report_filename report_package_pins.txt`

# `report_package_pins.tcl` details
`report_package_pins.tcl` makes a file `report_package_pins.txt` containing a text table.

# `analyze_report.py` details
Produces summary of pins by analyzing `report_package_pins.tcl` output txt file. Summaries are given in tables that are written in latex.

Below summary tables are produced:

- `table_pin_count_by_type.tex`  
    Table of `PACKAGE_PIN` count by type of pin. Counts all pins, pins connected to `PORT`, and pins connected to `NET`.  
    Priority of assigning type of pins is shown below (left is highest, right is lowest). 
    - types of pin: `I/O`, `MGT rx/tx`, `MGT refclk`, `Config`, `Monitor`, `Power/GND`, `Not Connected`  
    
- `table_port_with_no_net.tex`  
    Table of `PORT`s (with pin) that are not connected to `NET`.
    
- `table_io_pin_count_by_bank.tex`  
    Table of `I/O` `PACKAGE_PIN` count by FPGA bank.
    Counts all `I/O` pins, `I/O` pins connected to `PORT`, and `I/O` pins connected to `NET`.