// Behavioral and event-count regression for the ndnSIM scheduler adapter.
#include "ns3/core-module.h"
#include "ns3/ndnSIM/utils/ndn-time.hpp"
#include <ndn-cxx/util/scheduler.hpp>
#include <ndn-cxx/util/time-custom-clock.hpp>
#include <iostream>
#include <memory>
#include <vector>

struct Result { const char* name; bool callbacks; uint64_t events; uint64_t limit; };
int main() {
  using ns3::Simulator;
  ::ndn::time::setCustomClocks(std::make_shared<ns3::ndn::time::CustomSteadyClock>(),
                             std::make_shared<ns3::ndn::time::CustomSystemClock>());
  std::vector<Result> results;
  for(int mode=0;mode<3;++mode) {
    ::ndn::DummyIoService io;
    bool ok=true;
    int count=0,previous=0;
    {
      ::ndn::scheduler::Scheduler scheduler(io);
      std::vector<::ndn::scheduler::EventId> handles;
      for(int i=128;i>=1;--i) {
        handles.push_back(scheduler.schedule(::ndn::time::milliseconds(i),[&,i] {
          ok=ok && i>previous && Simulator::Now().GetNanoSeconds()==int64_t(i)*1000000;
          if(mode==1) ok=ok && i%2==0;
          previous=i; ++count;
        }));
      }
      if(mode==1) for(size_t i=0;i<handles.size();++i) if((128-int(i))%2) {
        handles[i].cancel(); handles[i].cancel();
      }
      if(mode==2) scheduler.cancelAllEvents();
      Simulator::Run();
      const int expected=mode==0?128:mode==1?64:0;
      results.push_back({mode==0?"replace-earliest":mode==1?"cancel-idempotently":"cancel-all",
                         ok && count==expected,Simulator::GetEventCount(),uint64_t(expected+4)});
    }
    Simulator::Destroy();
  }
  {
    ::ndn::DummyIoService io;
    bool ok=true; std::vector<int> calls;
    {
      ::ndn::scheduler::Scheduler scheduler(io);
      Simulator::ScheduleWithContext(7,ns3::NanoSeconds(0),[&] {
        scheduler.schedule(::ndn::time::milliseconds(1),[&] {
          ok=ok && Simulator::GetContext()==7 && Simulator::Now().GetNanoSeconds()==1000000;
          calls.push_back(1);
          scheduler.schedule(::ndn::time::nanoseconds(0),[&] {
            ok=ok && Simulator::GetContext()==7 && Simulator::Now().GetNanoSeconds()==1000000;
            calls.push_back(2);
          });
        });
      });
      Simulator::Run();
      results.push_back({"reentrant-zero-delay-and-context",ok && calls==std::vector<int>({1,2}),
                         Simulator::GetEventCount(),8});
    }
    Simulator::Destroy();
  }
  bool all=true;
  std::cout<<"{\"cases\":[";
  for(size_t i=0;i<results.size();++i) {
    const auto& r=results[i]; bool pass=r.callbacks && r.events<=r.limit; all=all && pass;
    if(i) std::cout<<',';
    std::cout<<"{\"case\":\""<<r.name<<"\",\"callbacks_and_timing_ok\":"<<(r.callbacks?"true":"false")
             <<",\"simulator_events\":"<<r.events<<",\"event_limit\":"<<r.limit
             <<",\"status\":\""<<(pass?"PASS":"FAIL")<<"\"}";
  }
  std::cout<<"],\"status\":\""<<(all?"PASS":"FAIL")<<"\"}\n";
  return all?0:1;
}
