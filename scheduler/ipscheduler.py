# vim: tabstop=4 shiftwidth=4 softtabstop=4 
# Copyright (c) 2013 OpenStack Foundation 
# All Rights Reserved. 
# 
#    Licensed under the Apache License, Version 2.0 (the "License"); you may 
#    not use this file except in compliance with the License. You may obtain 
#    a copy of the License at 
# 
#   http://www.apache.org/licenses/LICENSE-2.0 
# 
#    Unless required by applicable law or agreed to in writing, software 
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT 
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the 
#    License for the specific language governing permissions and limitations 
#    under the License.


import random
from nova import exception 
from nova.openstack.common import log as logging 
#from nova import flags 
from nova.scheduler import driver
#FLAGS = flags.FLAGS 
LOG = logging.getLogger(__name__)

class IPScheduler(driver.Scheduler):    
	"""    Implements Scheduler as a random node selector based on    IP address and hostname prefix.    """
	def _filter_hosts(self, hosts, hostname_prefix):
		"""Filter a list of hosts based on hostname prefix."""
		hosts = [host for host in hosts if host.startswith(hostname_prefix)]
		return hosts
		
		
	def _schedule(self, context, topic, request_spec, filter_properties):
		"""        Picks a host that is up at random based on        IP address and hostname prefix.        """
		elevated = context.elevated()
		hosts = self.hosts_up(elevated, topic)
 
		if not hosts:
			msg = _("Is the appropriate service running?")
			raise exception.NoValidHost(reason=msg)
		remote_ip = context.remote_address
		LOG.info('remote ip ',remote_ip)
		
		
		if remote_ip.startswith('10.1'):
			hostname_prefix = 'doc'
		elif remote_ip.startswith('10.2'):
			hostname_prefix = 'ops'
		else:
			hostname_prefix = 'dev'
			
			
		hosts = self._filter_hosts(hosts, hostname_prefix)
		host = hosts[int(random.random() * len(hosts))]

		LOG.debug(_("Request from %(remote_ip)s scheduled to %(host)s") % locals())
		return host
		
	
	def schedule_run_instance(self, context, request_spec,admin_password,injected_files,requested_networks,is_first_time,filter_properties):
		"""Attempts to run the instance""" 
		instance_uuids = request_spec.get('instance_uuids')        
		for num, instance_uuid in enumerate(instance_uuids):
			request_spec['instance_properties']['launch_index'] = num 
			try:
				host = self._schedule(context, 'compute', request_spec,filter_properties)      
				updated_instance = driver.instance_update_db(context,instance_uuid)
				self.compute_rpcapi.run_instance(context,instance=updated_instance,host=host,requested_networks=requested_networks,injected_files=injected_files,admin_password=admin_password,is_first_time=is_first_time,request_spec=request_spec,filter_properties=filter_properties)
				'''LOG.debug(_("context = %(context)s") % {'context': context.__dict__})
				LOG.debug(_("request_spec = %(request_spec)s") % locals())LOG.debug(_("filter_properties = %(filter_properties)s") % locals())'''

			except Exception as ex:
				# NOTE(vish): we don't reraise the exception here to make sure
                # that all instances in the request get set to
                # error properly
				driver.handle_schedule_error(context, ex, instance_uuid,request_spec)		
				
			
			
			
	def schedule_prep_resize(self, context, image, request_spec,filter_properties, instance, instance_type,reservations):
			"""Select a target for resize."""
			host = self._schedule(context,'compute',request_spec,filter_properties)
			self.compute_rpcapi.prep_resize(context, image, instance,instance_type, host, reservations) 
			
			
