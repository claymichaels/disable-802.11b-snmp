#!/usr/bin/python
__author__ = 'Clay'

from os.path import isfile
from sys import argv, path
path.insert(0, '/home/automation/scripts/clayScripts/resources/')
import claylib

logfile = open('/home/automation/scripts/clayScripts/ap_snmp_configurator/log', 'w')

# SNMP details
read_password = '<SNIPPED PW>'
snmp_set_prefix = 'snmpset -v 2c -c'
snmp_get_prefix = 'snmpget -v 2c -c'
oids = {'.1.3.6.1.4.1.388.11.3.4.1.8.1.1.1': 8}
#snmpset -v2c -c <SNIPPED PW> <SNIPPED IP>  .1.3.6.1.4.1.388.11.3.4.1.8.1.1.1 i 8


# db details
local_db_name = '/home/automation/scripts/clayScripts/websites/clay/resources/ap_snmp_802.11band.db'


def do_it(db, ip, con, pw):
    try:
        # Set then check
        cmd = ' '.join([snmp_set_prefix, pw, ip, '.1.3.6.1.4.1.388.11.3.4.1.8.1.1.1', 'i', '8'])
        result = con.execute_command(cmd)


        if 'SNMPv2-SMI::enterprises.388.11.3.4.1.8.1.1.1 = INTEGER: 8'  in result:
            query = 'UPDATE update_status SET status="TRUE" WHERE IP="%s";' % ip
            db.query(query)
            print('Updated %s!' % ip)
            return 'Updated'
        else:
            return 'Error! AP may not be in mesh, or SNMP password may be incorrect.'
    except KeyboardInterrupt:
        exit()


def connect_to_ccu(local_db, target, write_password, ips_needing_update):
    logfile.write('Scanning %s\'s consist for APs...\n' % target)
    ips_in_consist = []
    ips_to_update = []
    try:
        ccu_con = claylib.Connection('root', 'helpdesk', target)
        consist2 = ccu_con.execute_command('cat /var/local/consist2.txt').split('\n')
        for line in consist2:
            if line[:9] in ['10.125.1.', '10.125.3.', '10.125.4.', '10.125.9.', '10.125.10', '10.125.11', '10.125.12', '10.125.13', '10.125.14', '10.125.15', '10.125.18']:
                ips_in_consist.append(line.split(' ')[0])
                if line.split(' ')[0] in ips_needing_update:
                    ips_to_update.append(line.split(' ')[0])
        if len(ips_in_consist) is 0:
            logfile.write('\tNo APs detected!\n')
            return '%s:      No APs detected!' % target
        elif len(ips_to_update) is 0:
            logfile.write('\tAll APs in consist are already updated!\n')
            return "%s:       All APs in consist are already updated!" % target
        else:
            logfile.write('\tFound %d APs in need of update.\n' % len(ips_to_update))
            updated_aps = 0
            unupdated_aps = 0
            for ip in ips_to_update:
                result = do_it(local_db, ip, ccu_con, write_password)
                if 'Updated' in result:
                    updated_aps += 1
                else:
                    unupdated_aps += 1
                logfile.write('\t%s : %s\n' % (ip, result))
            ips_to_update = []
            return '%s:       Updated %i APs.     Unable to update %i.' % (target, updated_aps, unupdated_aps)
        ccu_con.disconnect()
        logfile.write('\tDisconnecting...\n')
    except KeyboardInterrupt:
        exit()
    except AttributeError:
        logfile.write('\tUnable to connect to %s\n' % target)
        return '%s:        Unable to connect to CCU' % target


# For loop!
def main():
    local_db = claylib.Sqlite_db(local_db_name)
    local_db.open()
    ips_needing_update = local_db.query('SELECT ip FROM update_status WHERE status="FALSE"')
    # GET ALL CCUs
    ccu_list = claylib.query_nomad_db('amec.fleetman', 'fleetman', 'nomadsda', 'Pr1vat3access', 'select obj_train.fleet_id, obj_fleet.fleet_name, obj_train.train_ref from obj_train left join obj_fleet on obj_train.fleet_id=obj_fleet.fleet_id where obj_train.in_service="Y" and obj_fleet.fleet_id in (13, 18);')
    # FOR LOOP GOES HERE
    for ccu in ccu_list:
        target_ccu = '%s.%s' % (ccu[1].lower(), ccu[2].lower())
        print('%s:' % target_ccu)
        write_password = '<SNIPPED PW>'
        result = connect_to_ccu(local_db, target_ccu, write_password, ips_needing_update)
        if 'Updated' in result:
            print(result)


main()
