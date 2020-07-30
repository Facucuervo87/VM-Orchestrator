# pylint: disable=import-error
import VM_OrchestratorApp.tasks as tasks
from VM_OrchestratorApp.src.utils import slack, mongo
import VM_OrchestratorApp.tasks as tasks

from celery import chain, chord

import copy
import pandas as pd
from VM_Orchestrator.settings import settings

def get_resources_from_target(information):
    execution_chain = chain(
        tasks.send_email_with_resources_for_verification.si(information).set(queue='slow_queue')
    )
    execution_chain.apply_async(queue='fast_queue', interval=300)

def recon_against_target(information):
    information['is_first_run'] = True
    information['language'] = 'eng'
    information['priority'] = None
    information['exposition'] = None
    information['type'] = 'domain'

    slack.send_notification_to_channel('_ Starting recon only scan against %s _' % information['domain'], '#vm-ondemand')
    execution_chain = chain(
        tasks.run_recon.si(information).set(queue='slow_queue')
    )
    execution_chain.apply_async(queue='fast_queue', interval=300)

def on_demand_scan(information):

    information['is_first_run'] = True
    information['language'] = 'eng'

    # The "Information" argument on chord body is temporary

    if information['type'] == 'domain':
        slack.send_notification_to_channel('_ Starting on demand scan of type domain against %s _' % information['domain'], '#vm-ondemand')
        execution_chain = chain(
            tasks.run_recon.si(information).set(queue='slow_queue'),
            chord(
                [
                    tasks.run_web_scanners.si(information).set(queue='fast_queue'),
                    tasks.run_ip_scans.si(information).set(queue='slow_queue')
                ],
                body=tasks.on_demand_scan_finished.s(information).set(queue='fast_queue'),
                immutable = True
            )
        )
        execution_chain.apply_async(queue='fast_queue', interval=300)
    elif information['type'] == 'ip':
        slack.send_notification_to_channel('_ Starting on demand scan of type ip against %s _' % information['resource'], '#vm-ondemand')
        execution_chord = chord(
                [
                    tasks.run_ip_scans.si(information).set(queue='slow_queue')
                ],
                body=tasks.on_demand_scan_finished.s(information).set(queue='fast_queue'),
                immutable = True
            )
        execution_chord.apply_async(queue='fast_queue', interval=300)
    elif information['type'] == 'url':
        slack.send_notification_to_channel('_ Starting on demand scan of type url against %s _' % information['resource'], '#vm-ondemand')
        execution_chord = chord(
                [
                    tasks.run_web_scanners.si(information).set(queue='fast_queue'),
                    tasks.run_ip_scans.si(information).set(queue='slow_queue')
                ],
                body=tasks.on_demand_scan_finished.s(information).set(queue='fast_queue'),
                immutable = True
            )
        execution_chord.apply_async(queue='fast_queue', interval=300)