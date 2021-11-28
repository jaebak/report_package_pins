# Description: Makes a table txt file containing PACKAGE_PIN information (e.g. PORT and NET)
# Table includes following columns: PACKAGE_PIN, PIN_FUNC, SITE, SITE_TYPE, BANK, DIRECTION, PORT, NET 
# Requirements: A Vivado project and an implemented design
# Run method: There are two methods of runing this script
#   Method 1)
#     vivado -nojournal -nolog -mode batch -source report_package_pins.tcl -tclargs PATH_TO_PROJECT.xpr DESIGN_NAME OUTPUT_FILENAME
#     Example: vivado -nojournal -nolog -mode batch -source report_package_pins.tcl -tclargs project.xpr impl_1 report_package_pins.txt"
#   Method 2)
#     vivado -nojournal -nolog -mode tcl
#     set argc 3
#     set argv [list PATH_TO_PROJECT.xpr DESIGN_NAME OUTPUT_FILENAME]"
#     source report_package_pins.tcl
# Author: Jaebak Kim
# Version: 1.0

if {$argc != 3} {
  puts "Please use one of the below two methods"
  puts "   Method 1)"
  puts "     vivado -mode batch -source report_package_pins.tcl -tclargs PATH_TO_PROJECT.xpr DESIGN_NAME OUTPUT_FILENAME"
  puts "     (e.g.) vivado -mode batch -source report_package_pins.tcl -tclargs project.xpr impl_1 report_package_pins.txt"
  puts "   Method 2)"
  puts "     vivado -mode tcl"
  puts "     set argc 3"
  puts "     set argv \[list PATH_TO_PROJECT.xpr DESIGN_NAME OUTPUT_FILENAME\]"
  puts "     source report_package_pins.tcl"
} else { 
  set project_path  [lindex $argv 0]
  set design  [lindex $argv 1]
  set output_filename [lindex $argv 2]

  # Open project
  open_project $project_path
  # Open implemented design
  open_run $design
  
  # Set report string
  set reportString ""
  append reportString "+-----------------------------------------------------------------------------------------------\n"
  append reportString "| Report   :  report_package_pins\n"
  append reportString "| Design   :  [get_property -quiet TOP [current_design -quiet]]\n"
  append reportString "| Part     :  [get_property -quiet PART [current_project -quiet]]\n"
  append reportString "| Version  :  [lindex [split [version] \n] 0] [lindex [split [version] \n] 1]\n"
  append reportString "| Date     :  [clock format [clock seconds]]\n"
  append reportString "+-----------------------------------------------------------------------------------------------\n\n"
  
  # Make table containing pin information
  set table [xilinx::designutils::prettyTable {Package Pins Summary}]
  $table header [list "PACKAGE_PIN" "PIN_FUNC" "SITE" "SITE_TYPE" "BANK" "DIRECTION" "PORT" "NET"]
  foreach pin [get_package_pins] { 
    set site [get_sites -of_objects $pin]; 
    set port [get_ports -of_objects $pin]; 
    set net [get_nets -of_objects $port]; 
    set direction ""; if {$port!=""} {
      set direction [get_property DIRECTION $port]
    }; 
    set site_type ""; 
    if {$site!=""} {
      set site_type [get_property SITE_TYPE $site]
    }; 
    $table addrow [list $pin [get_property PIN_FUNC $pin] $site $site_type [get_property BANK $pin] $direction $port [get_nets -of_objects $port] ]
  }
  append reportString "[$table print]"
  
  # Print report
  puts $reportString

  # Save report to file
  puts "Creating $output_filename"
  set outFile [open $output_filename w]
  puts $outFile $reportString
  close $outFile
}
