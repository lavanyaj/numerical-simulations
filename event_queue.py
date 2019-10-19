import heapq

class EventQueue:
    def __init__(self):
        self.heap = []
        self.last_event_time = 0
        self.last_event_id = 0
        self.total_scheduled = 0
        self.total_simulated = 0
        return

    def has_events(self):
        return len(self.heap) > 0

    def get_last_time(self):
        return self.last_event_time

    def get_total_simulated(self):
        return self.total_simulated
    
    def get_last_id(self):
        return self.last_event_id
    
    def schedule(self, ev_str, delay):
        ev_time = self.get_last_time()+delay
        ev_id = self.total_scheduled
        event = (ev_time, ev_id, ev_str)
         
        self.total_scheduled += 1
        heapq.heappush(self.heap, event)
        return
    
    def get_next_event(self):
        if len(self.heap) == 0:
            return None
        event = heapq.heappop(self.heap)
        self.total_simulated += 1
        self.last_event_time = event[0]
        self.last_event_id = event[1]
        return event

    # start flow now
    def schedule_start_flow(self, flow_id, delay=0):
        event_str = "start flow " + str(flow_id)
        self.schedule(event_str, delay)
        return

    def schedule_stop_flow(self, flow_id, delay=0):
        event_str = "stop flow " + str(flow_id)
        self.schedule(event_str, delay)
        return

    def schedule_process_flow_at_hop(self, flow_id, hop, direction, delay):
        event_str\
            = "process flow " + str(flow_id)\
            + " at hop " + str(hop)\
            + " direction " + str(direction)

        self.schedule(event_str, delay)
        return

    def schedule_check_rates(self,  delay, end_time):
        # add to string so we can check when re-scheduling
        event_str = "check rates until " + str(int(end_time))
        self.schedule(event_str, delay)
        return

def main():
    eq = EventQueue()
    eq.schedule_start_flow(flow_id="A", delay=0)
    eq.schedule_stop_flow(flow_id="A", delay=500)
    eq.schedule_check_rates(200, 2000)
    eq.schedule_process_flow_at_hop\
        (flow_id="A", hop=1, direction=1, delay=200)
    while eq.has_events():
        ev = eq.get_next_event()
        #print eq.last_event_time, ": ", ev

#main()
