#!/usr/bin/env python3
# Author: Jaebak
# Version: 1.0
# Description: Produces summary of pins by analyzing 'report_package_pins.tcl' output txt file.
#   Summaries are given in tables that are written in latex.
import os
import sys
import argparse
import re
import sqlite3

# Convets report file to below sqlite table
#   pins (package_pin, pin_func, site, site_type, bank, direction, port, net)
# Input:
#   db_cur: cursor to sqlite db
def convert_report_to_pins_table(report_filename, db_cur):
  # Create table
  db_cur.execute(
  '''CREATE TABLE pins (
       package_pin text PRIMARY KEY,
       pin_func text,
       site text,
       site_type text,
       bank integer,
       direction text,
       port text,
       net text
  );''')
  # Fill table
  with open(report_filename) as report_file:
    passed_summary_line = False
    for line in report_file:
      if "Package Pins Summary" in line: 
        passed_summary_line = True
        report_file.readline() # skip +---- line
        report_file.readline() # skip table header
        report_file.readline() # skip +---- line
        continue
      if passed_summary_line:
        if '+-' == line[0:2]: break # Table has ended
        line_split = line.split('|')[1:-1]
        clean_line_split = [item.strip() for item in line_split]
        #sql_data = [pin, pin_func, site, site_type, bank, direction, port, net]
        sql_data = [None if item=='' else item for item in clean_line_split]
        #print(sql_data)
        ## Insert data
        db_cur.execute("INSERT INTO pins(package_pin, pin_func, site, site_type, bank, direction, port, net) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", sql_data)

# Create below table using pins table 
#   pins_type (package_pin, pin_type) where pin_type = [io, not_connected, configuration, monitor, power_gnd, mgt_refclk, mgt_rx_tx]
# Input:
#   db_cur: cursor to sqlite db
def create_pins_type_table(db_cur):
  # Get information
  db_cur.execute('SELECT package_pin, pin_func FROM pins')
  # pin_func = [(pin, pin_func)]
  pin_func_list = db_cur.fetchall()

  # Make pins_type table
  db_cur.execute(
  '''CREATE TABLE pins_type (
       package_pin text PRIMARY KEY,
       pin_type text
  );''')
  for pin, pin_func in pin_func_list:
    pin_type = None
    # Divide pin_func into pin_type 
    if re.match('^io', pin_func, re.IGNORECASE): pin_type = 'io'
    elif re.match('^mgtrefclk', pin_func, re.IGNORECASE): pin_type = 'mgt_refclk'
    elif re.match('^mgth[r|t]', pin_func, re.IGNORECASE): pin_type = 'mgt_rx_tx'
    elif re.match('^m[0-2]_0$|^d0[0-9]|^cclk_0$|^done_0$|^tdo_0$|^tms_0$|^tdi_0$|^tck_0$|^init_b_0$|^pudc_b_0$|^program_b_0$|^por_override$|^cfgbvs_0$|^rdwr_fcs_b_0$',pin_func, re.IGNORECASE): pin_type = 'configuration'
    elif re.match('^vn$|^vp$|^dxn$|^dxp$|^gndadc$', pin_func, re.IGNORECASE): pin_type = 'monitor'
    elif re.match('^vcc|^vref|^vbatt$|^gnd$', pin_func, re.IGNORECASE): pin_type = 'power_gnd'
    elif re.match('^mgtavtt|^mgtavcc|^mgtvccaux|^mgtrref_r$', pin_func, re.IGNORECASE): pin_type = 'power_gnd'
    elif re.match('^nc$', pin_func, re.IGNORECASE): pin_type = 'not_connected'
    else:
      print('Unknown pin type', pin, pin_func)
    # Fill pins_type table
    db_cur.execute("INSERT INTO pins_type(package_pin, pin_type) VALUES(?,?)", (pin, pin_type))

# Fetches data from db with sql_string
# Input:
#   db_cur: cursor to sqlite db
# Output: []
def get_data(db_cur, sql_string):
  db_cur.execute(sql_string)
  return db_cur.fetchall()

# Output: sql string for joined table of pins and pins_type sql tables
# Below are format of sql tables
#   pins (package_pin, pin_func, site, site_type, bank, direction, port, net)
#   pins_type (package_pin, pin_type) where pin_type = [io, not_connected, configuration, monitor, power_gnd, mgt_refclk, mgt_rx_tx]
def pins_sql(select_string, filter_string=""):
  if (filter_string==""): return "SELECT "+select_string+' FROM pins INNER JOIN pins_type ON pins_type.package_pin = pins.package_pin'
  else: return "SELECT "+select_string+' FROM pins INNER JOIN pins_type ON pins_type.package_pin = pins.package_pin WHERE '+filter_string

# Returns dict of pins categories by column_name from sql table
# Sql table format follows pins_sql()
# Input: 
#   db_cur: cursor to sqlite db
#   column_name: column name in sql table
#   filter_string: sql_string that goes after WHERE to filter results
#   select_string: sql_string that goes after SELECT to select results
# Output: pins_column[column_values] = [pin]
def get_pins_by_column(db_cur, column_name, filter_string="", select_string='pins.package_pin'):
  # Find column values
  column_values = [item[0] for item in get_data(db_cur, pins_sql('DISTINCT '+column_name)) if item[0] != None]
  #print(column_values)
  pins_column = {}
  for column_value in column_values:
    pins_column[column_value] = get_data(db_cur, pins_sql(select_string, ' '.join([column_name+"='"+str(column_value)+"'", "" if filter_string=="" else ("AND "+filter_string)])))
  return pins_column

# Makes a latex table from table_data with filename
# table_data format: [ [value] or latex string ]
# Each row in table is filled with item in table_data
#   If item is list, row = [value]
#   If item is string, string will be inserted
# Input:
#   table_data: [ latex string or [value] ]
#   filename: output latex filename
#   table_spec: table_spec of tabular latex table
# Output: Latex file with filename
def make_latex_table(table_data, filename, table_spec=''):
  filename_no_ext = os.path.splitext(filename)[0]
  # Get number of columns
  n_columns = -1
  for row in table_data:
    if isinstance(row, list): 
      n_columns = len(row)
      break

  # Space for columns
  columns_space = [-1]*n_columns
  for row in table_data:
    if not isinstance(row, list): continue
    for index, item in enumerate(row):
      if columns_space[index] < len(str(item)): columns_space[index] = len(str(item).replace('#','\\#').replace('_','\\_'))

  # Make latex table
  with open(filename, 'w') as latex_table:
    # Write header
    latex_table.write('\\documentclass[10pt,oneside]{report}\n')
    latex_table.write('\\usepackage{booktabs}\n')
    latex_table.write('\\usepackage[active,tightpage]{preview}\n')
    latex_table.write('\\begin{document}\n')
    latex_table.write('\\begin{preview}\n')
    latex_table.write('\\begin{tabular}{'+(('' if n_columns <=0 else 'l'+'r'*(n_columns-1)) if table_spec=='' else table_spec)+'}'+'\n')
    # Write rows
    for row in table_data:
      latex_string = ''
      if isinstance(row, str): latex_string = row
      elif isinstance(row, list): 
        row_strings = []
        for index, item in enumerate(row): row_strings.append((' '+str(item).replace('#','\\#').replace('_','\\_')+' ').ljust(columns_space[index]+2))
        latex_string = '&'.join(row_strings) + '\\\\'
      latex_table.write(latex_string+'\n')
    # Write tailer
    latex_table.write('\\end{tabular}\n')
    latex_table.write('\\end{preview}\n')
    latex_table.write('\\end{document}\n')

  print('Wrote to '+filename)
  print('Run below command to compile')
  print('  pdflatex '+filename+' && rm -f '+os.path.basename(filename_no_ext)+'.aux '+os.path.basename(filename_no_ext)+'.log && mv -f '+os.path.basename(filename_no_ext)+'.pdf '+os.path.dirname(filename_no_ext)+' && open '+filename_no_ext+'.pdf\n')
    

if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='''\
Produces summary of pins by analyzing 'report_package_pins.tcl' output txt file.
Summaries are given in tables that are written in latex.

Below summary tables are produced:
- table_pin_count_by_type.tex
    Table of PACKAGE_PIN count by type of pin. 
    Priority of assigning type of pins is shown below (left is highest, right is lowest).
    - types of pin: I/O, MGT rx/tx, MGT refclk, Config, Monitor, Power/GND, Not Connected
    Counts all pins, pins connected to PORT, and pins connected to NET.
- table_port_with_no_net.tex
    Table of PORTs (with pin) that are not connected to NET.
- table_io_pin_count_by_bank.tex
    Table of I/O PACKAGE_PIN count by FPGA bank.
    Counts all I/O pins, I/O pins connected to PORT, and I/O pins connected to NET.
''', formatter_class=argparse.RawTextHelpFormatter)

  parser.add_argument('-r', '--input_report_filename', required=True, help="txt file of 'report_package_pins.tcl' output")
  parser.add_argument('-v', '--verbose', action="store_true", help='Prints basic pin summary')
  parser.add_argument('-f', '--force', action="store_true", help='Forces output to be written even if output file exists')
  parser.add_argument('-o', '--output_folder', default='./table', help='Output folder for summary table files written in latex. (default: ./table)')

  args = parser.parse_args()

  # Check input arguments
  argument_error = False
  # Check if input file exists
  if not os.path.isfile(args.input_report_filename):
    print('[Error] Input file (REPORT_FILENAME: '+args.input_report_filename+') does not exist')
    print("  Run 'report_package_pins.tcl' to produce 'report_package_pins.txt'")
    argument_error = True
  # Check if output file exists
  if not args.force:
    table_filenames = ['table_pin_count_by_type.tex', 'table_port_with_no_net.tex', 'table_io_pin_count_by_bank.tex']
    for filename in table_filenames:
      if os.path.isfile(os.path.join(args.output_folder, filename)):
        print('[Error] Output file '+str(os.path.join(args.output_folder, filename))+' exists')
        print('  Please rename or remove the output file or use --force argument')
        argument_error = True
  if argument_error:
    sys.exit()

  # Create output folder
  if not os.path.isdir(args.output_folder):
    os.makedirs(args.output_folder)

  # Create db
  database = sqlite3.connect(':memory:')
  db_cur = database.cursor()

  # Convets report file to below sqlite table
  #   pins (package_pin, pin_func, site, site_type, bank, direction, port, net)
  convert_report_to_pins_table(args.input_report_filename, db_cur)
  #print(get_data(db_cur, "SELECT * FROM pins"))

  # Create below table using pins table
  #   pins_type (package_pin, pin_type) where pin_type = [io, not_connected, monitor, power_gnd, mgt_refclk, mgt_rx_tx]
  create_pins_type_table(db_cur)
  #print(get_data(db_cur, "SELECT * FROM pins_type"))

  # Get information from db
  # pins_types[io/nc/configuration/monitor/power/mgt_refclk/mgt_rx_tx] = [pin]
  pins_type = get_pins_by_column(db_cur, column_name="pin_type")
  # pins_type_with_port[io/nc/configuration/monitor/power/mgt_refclk/mgt_rx_tx] = [pin]
  pins_type_with_port = get_pins_by_column(db_cur, column_name="pin_type", filter_string='port IS NOT NULL')
  # pins_type_with_net[io/nc/configuration/monitor/power/mgt_refclk/mgt_rx_tx] = [pin]
  pins_type_with_net = get_pins_by_column(db_cur, column_name="pin_type", filter_string='net IS NOT NULL')
  # net_with_no_port = [pin]
  net_with_no_port = get_data(db_cur, pins_sql(select_string='pins.package_pin', filter_string='net IS NOT NULL AND port IS NULL'))
  # port_with_no_net = [pin, port]
  port_with_no_net = get_data(db_cur, pins_sql(select_string='pins.package_pin, port', filter_string='port IS NOT NULL AND net IS NULL'))
  sorted(port_with_no_net)
  # pins_bank[bank] = [pin]
  pins_bank = get_pins_by_column(db_cur, column_name="bank", filter_string="pin_type=='io'")
  pins_bank = {key:val for key, val in pins_bank.items() if len(val) != 0} # Remove banks with no pins
  # pins_bank_with_port[bank] = [pin]
  pins_bank_with_port = get_pins_by_column(db_cur, column_name="bank", filter_string="pin_type=='io' AND port IS NOT NULL")
  pins_bank_with_port = {key:val for key, val in pins_bank_with_port.items() if len(val) != 0} # Remove banks with no pins
  # pins_bank_with_net[bank] = [pin]
  pins_bank_with_net = get_pins_by_column(db_cur, column_name="bank", filter_string="pin_type=='io' AND net IS NOT NULL")
  pins_bank_with_net = {key:val for key, val in pins_bank_with_net.items() if len(val) != 0} # Remove banks with no pins

  # Print basic information
  if args.verbose:
    print('Count report')
    print('  [All ] Number of io: '+str(len(pins_type['io']))+' nc: '+str(len(pins_type['not_connected']))+' configuration: '+str(len(pins_type['configuration']))+' monitor: '+str(len(pins_type['monitor']))+' power: '+str(len(pins_type['power_gnd']))+' refclk: '+str(len(pins_type['mgt_refclk']))+' rx_tx: '+str(len(pins_type['mgt_rx_tx'])))
    print('  [PORT] Number of io: '+str(len(pins_type_with_port['io']))+' nc: '+str(len(pins_type_with_port['not_connected']))+' configuration: '+str(len(pins_type_with_port['configuration']))+' monitor: '+str(len(pins_type_with_port['monitor']))+' power: '+str(len(pins_type_with_port['power_gnd']))+' refclk: '+str(len(pins_type_with_port['mgt_refclk']))+' rx_tx: '+str(len(pins_type_with_port['mgt_rx_tx'])))
    print('  [NET ] Number of io: '+str(len(pins_type_with_net['io']))+' nc: '+str(len(pins_type_with_net['not_connected']))+' configuration: '+str(len(pins_type_with_net['configuration']))+' monitor: '+str(len(pins_type_with_net['monitor']))+' power: '+str(len(pins_type_with_net['power_gnd']))+' refclk: '+str(len(pins_type_with_net['mgt_refclk']))+' rx_tx: '+str(len(pins_type_with_net['mgt_rx_tx'])))
    print('  Number of NETs  with no PORT: '+str(len(net_with_no_port)))
    print('  Number of PORTs with no NET: '+str(len(port_with_no_net))+'\n')

  # Make latex table of number of pins per pin_type [Use pins_type, pins_type_with_port, pins_type_with_net]
  pin_count_table = []
  pin_count_table.append('\\hline\\hline')
  pin_count_table.append(['Pin type', '# pins', '# pins with PORT', '# pins with NET'])
  pin_count_table.append('\\hline')
  pin_count_table.append(['I/O', len(pins_type['io']), len(pins_type_with_port['io']), len(pins_type_with_net['io'])])
  pin_count_table.append(['MGT rx/tx', len(pins_type['mgt_rx_tx']), len(pins_type_with_port['mgt_rx_tx']), len(pins_type_with_net['mgt_rx_tx'])])
  pin_count_table.append(['MGT refclk', len(pins_type['mgt_refclk']), len(pins_type_with_port['mgt_refclk']), len(pins_type_with_net['mgt_refclk'])])
  pin_count_table.append(['Config', len(pins_type['configuration']), len(pins_type_with_port['configuration']), len(pins_type_with_net['configuration'])])
  pin_count_table.append(['Monitor', len(pins_type['monitor']), len(pins_type_with_port['monitor']), len(pins_type_with_net['monitor'])])
  pin_count_table.append(['Power/GND', len(pins_type['power_gnd']), len(pins_type_with_port['power_gnd']), len(pins_type_with_net['power_gnd'])])
  pin_count_table.append(['Not Connected', len(pins_type['not_connected']), len(pins_type_with_port['not_connected']), len(pins_type_with_net['not_connected'])])
  # Count total pins for pins_type, pins_type_with_port, pins_type_with_net
  total_count = [0, 0, 0]
  for pin_type in pins_type: 
    total_count[0] += len(pins_type[pin_type])
    total_count[1] += len(pins_type_with_port[pin_type])
    total_count[2] += len(pins_type_with_net[pin_type])
  pin_count_table.append(['Total', total_count[0], total_count[1], total_count[2]])
  pin_count_table.append('\\hline\\hline')
  make_latex_table(pin_count_table, os.path.join(args.output_folder,'table_pin_count_by_type.tex'))

  # Make latex table of ports with no net [Use port_with_no_net]
  port_no_net_table = []
  port_no_net_table.append('\\hline\\hline')
  port_no_net_table.append(['Index', 'Port', 'Pin'])
  port_no_net_table.append('\\hline')
  for index, (pin, port) in enumerate(port_with_no_net):
    port_no_net_table.append([index+1, port, pin])
  port_no_net_table.append('\\hline\\hline')
  make_latex_table(port_no_net_table, os.path.join(args.output_folder,'table_port_with_no_net.tex'))

  # Make latex table of number of (pins/pins with port) per bank [Use pins_bank, pins_bank_with_port]
  bank_count_table = []
  bank_count_table.append('\\hline\\hline')
  bank_count_table.append(['Bank']+[bank for bank in sorted(pins_bank)]+['Total'])
  bank_count_table.append('\\hline')
  bank_count_table.append(['# I/O pins']+[len(pins_bank[bank]) for bank in sorted(pins_bank)]+[sum([len(pins_bank[bank]) for bank in sorted(pins_bank)])])
  bank_count_table.append(['# I/O pins with PORT']+[len(pins_bank_with_port[bank]) for bank in sorted(pins_bank_with_port)]+[sum([len(pins_bank_with_port[bank]) for bank in sorted(pins_bank_with_port)])])
  bank_count_table.append(['# I/O pins with NET']+[len(pins_bank_with_net[bank]) for bank in sorted(pins_bank_with_net)]+[sum([len(pins_bank_with_net[bank]) for bank in sorted(pins_bank_with_net)])])
  bank_count_table.append('\\hline\\hline')
  make_latex_table(bank_count_table, os.path.join(args.output_folder, 'table_io_pin_count_by_bank.tex'))
