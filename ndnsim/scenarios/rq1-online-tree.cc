// Controlled IFA mechanism ifapilot; no detector or ML. Collector inputs come exclusively from received NDN Data.
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/ndnSIM-module.h"
#include "ns3/ndnSIM/apps/ndn-app.hpp"
#include "ns3/ndnSIM/NFD/daemon/fw/forwarder.hpp"
#include <boost/property_tree/json_parser.hpp>
#include <fstream>
#include <iomanip>
#include <map>
#include <set>
#include <sstream>
#include <vector>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <cmath>


#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <chrono>
#include <cstring>
namespace onlinebridge {
int fd=-1; uint64_t failures=0, sent=0, origin=0; sockaddr_un address;
uint64_t Mono() { return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
void Emit(const std::string& event, const std::string& detail="") {
  std::ostringstream s; s<<std::setprecision(17)<<event<<'|'<<ns3::Simulator::Now().GetSeconds()<<'|'<<Mono()<<'|'<<detail;
  auto v=s.str(); auto n=sendto(fd,v.data(),v.size(),MSG_DONTWAIT,reinterpret_cast<sockaddr*>(&address),sizeof(address));
  if(n!=static_cast<ssize_t>(v.size())) ++failures; else ++sent;
}
void Frame(uint32_t seq) { Emit("F",std::to_string(seq)); }
void Init(const std::string& path) {
  if(path.size()>=sizeof(address.sun_path)) throw std::runtime_error("IPC path too long");
  fd=socket(AF_UNIX,SOCK_DGRAM|SOCK_NONBLOCK,0); if(fd<0) throw std::runtime_error("socket failed");
  std::memset(&address,0,sizeof(address));address.sun_family=AF_UNIX;std::strcpy(address.sun_path,path.c_str());
}
}

// Packet classification reads the actual PPP + NDN/NDNLP wire, never CSV or tags.
#include "ns3/ppp-header.h"
#include <ndn-cxx/lp/packet.hpp>
#include <algorithm>

namespace ns3 { namespace ifapilot {
std::ofstream queueAudit, wireAudit;
std::string priorityPrefix;
uint32_t priorityWindows=28;
struct Traffic { std::string type="unknown", name="-"; bool high=false; };
Traffic Classify(Ptr<const Packet> packet) {
  Traffic t;
  try {
    if(packet->GetSize()<4) return t;
    auto p=packet->Copy(); PppHeader ppp; p->RemoveHeader(ppp);
    if(ppp.GetProtocol()!=0x0077) return t;
    std::vector<uint8_t> bytes(p->GetSize()); p->CopyData(bytes.data(),bytes.size());
    ::ndn::Block b(::ndn::make_span(bytes.data(),bytes.size()));
    bool nack=false;
    if(b.type()==::ndn::lp::tlv::LpPacket) {
      ::ndn::lp::Packet lp(b);
      if(lp.has<::ndn::lp::FragCountField>() && lp.get<::ndn::lp::FragCountField>()!=1) { t.type="fragment"; return t; }
      nack=lp.has<::ndn::lp::NackField>();
      ::ndn::Buffer::const_iterator first,last;
      std::tie(first,last)=lp.get<::ndn::lp::FragmentField>(0);
      if(first==last) return t;
      b=::ndn::Block(::ndn::make_span(&*first,std::distance(first,last)));
    }
    ::ndn::Name name;
    if(b.type()==::ndn::tlv::Interest) { ::ndn::Interest i(b); name=i.getName(); t.type=nack?"Nack":"Interest"; }
    else if(b.type()==::ndn::tlv::Data) { ::ndn::Data d(b); name=d.getName(); t.type="Data"; }
    else return t;
    t.name=name.toUri();
    // Exact workload allowlist, not an arbitrary substring or a user-supplied QoS tag.
    if(!nack && name.size()==4 && name.getPrefix(2).toUri()==priorityPrefix) {
      auto router=name.at(2).toUri(), seq=name.at(3).toUri();
      for(uint32_t r=1;r<=10;++r) if(router=="R"+std::to_string(r))
        for(uint32_t w=1;w<=priorityWindows;++w) if(seq==std::to_string(w)) t.high=true;
    }
  } catch(const std::exception&) { t.type="unknown"; t.name="-"; t.high=false; }
  return t;
}

// Shared 100-packet buffer. Stable FIFO within each class, non-preemptive service.
// Priority admission can evict the last normal packet when full. No extra capacity.
class ReportQueue : public Queue<Packet> {
public:
  static TypeId GetTypeId() {
    static TypeId t=TypeId("ns3::ifapilot::ReportQueue").SetParent<Queue<Packet>>()
      .AddConstructor<ReportQueue>(); return t;
  }
  bool priority=false;
  std::string from,to;
  void Log(const char* event,Ptr<const Packet> p) const {
    auto t=Classify(p);
    queueAudit<<std::setprecision(12)<<Simulator::Now().GetSeconds()<<','<<from<<','<<to<<','
      <<event<<','<<p->GetUid()<<','<<p->GetSize()<<','<<t.type<<','<<t.name<<','<<t.high<<','<<GetNPackets()<<'\n';
  }
  bool Enqueue(Ptr<Packet> p) override {
    const bool high=priority && Classify(p).high;
    Log("attempt",p);
    if(high && GetNPackets()>=GetMaxSize().GetValue()) {
      auto victim=end();
      for(auto it=begin();it!=end();++it) if(!Classify(*it).high) victim=it;
      if(victim!=end()) { auto dropped=DoRemove(victim); Log("evict",dropped); }
    }
    auto pos=end();
    if(high) for(auto it=begin();it!=end();++it) if(!Classify(*it).high) { pos=it; break; }
    bool ok=DoEnqueue(pos,p); Log(ok?"enqueue":"drop_tail",p); return ok;
  }
  Ptr<Packet> Dequeue() override {
    auto p=DoDequeue(begin()); if(p) Log("dequeue",p); return p;
  }
  Ptr<Packet> Remove() override {
    auto p=DoRemove(begin()); if(p) Log("remove",p); return p;
  }
  Ptr<const Packet> Peek() const override { return DoPeek(begin()); }
};
NS_OBJECT_ENSURE_REGISTERED(ReportQueue);
void WireTrace(std::string from,std::string to,std::string event,Ptr<const Packet> p) {
  auto t=Classify(p);
  wireAudit<<std::setprecision(12)<<Simulator::Now().GetSeconds()<<','<<from<<','<<to<<','<<event<<','
    <<p->GetUid()<<','<<p->GetSize()<<','<<t.type<<','<<t.name<<','<<t.high<<'\n';
}
int QueueSelfTest() {
  priorityPrefix="/report/selftest"; priorityWindows=28;
  unsigned checks=0;
  auto require=[&checks](bool ok) { if(!ok) throw std::runtime_error("Queue self-test failed at "+std::to_string(checks)); ++checks; };
  auto packet=[](const ::ndn::Block& b) { auto p=Create<Packet>(b.wire(),b.size()); PppHeader h; h.SetProtocol(0x0077); p->AddHeader(h); return p; };
  auto interest=[&packet](std::string name) { ::ndn::Interest i{::ndn::Name(name)}; i.setNonce(123); return packet(i.wireEncode()); };
  auto low1=interest("/background/selftest/BG1/1"),low2=interest("/benign/selftest/C1/1");
  auto high1=interest(priorityPrefix+"/R1/1"), high2=interest(priorityPrefix+"/R10/28");
  require(Classify(high1).high && Classify(high2).high);
  require(!Classify(low1).high && !Classify(low2).high);
  for(auto n:{"/reportx/selftest/R1/1","/report/other/R1/1","/report/selftest/R11/1","/report/selftest/R1/29","/report/selftest/R1/01","/report/selftest/R1/1/extra","/ifa/selftest/A1/1"}) require(!Classify(interest(n)).high);
  require(!Classify(Create<Packet>(1)).high);
  ::ndn::Interest i{::ndn::Name(priorityPrefix+"/R1/1")}; i.setNonce(123); auto b=i.wireEncode();
  ::ndn::lp::Packet lp; lp.set<::ndn::lp::FragmentField>(std::make_pair(b.begin(),b.end()));
  require(Classify(packet(lp.wireEncode())).high);
  ::ndn::lp::NackHeader nack; nack.setReason(::ndn::lp::NackReason::CONGESTION); lp.set<::ndn::lp::NackField>(nack);
  require(Classify(packet(lp.wireEncode())).type=="Nack" && !Classify(packet(lp.wireEncode())).high);
  lp.clear<::ndn::lp::NackField>(); lp.set<::ndn::lp::FragCountField>(2); lp.set<::ndn::lp::FragIndexField>(0);
  require(Classify(packet(lp.wireEncode())).type=="fragment" && !Classify(packet(lp.wireEncode())).high);
  ::ndn::Data d{::ndn::Name(priorityPrefix+"/R1/1")};
  d.setSignatureInfo(::ndn::SignatureInfo(static_cast<::ndn::tlv::SignatureTypeValue>(255)));
  d.setSignatureValue(::ndn::make_shared<::ndn::Buffer>(1,0));
  require(Classify(packet(d.wireEncode())).high);
  for(bool enabled:{false,true}) {
    auto q=CreateObject<ReportQueue>(); q->SetMaxSize(QueueSize("3p")); q->priority=enabled;
    require(q->Enqueue(low1) && q->Enqueue(low2) && q->Enqueue(high1));
    require(q->GetNPackets()==3);
    require(q->Enqueue(high2)==enabled);
    require(q->GetNPackets()==3 && q->GetTotalDroppedPackets()==1);
    require(q->Dequeue()==(enabled?high1:low1));
    require(q->Dequeue()==(enabled?high2:low2));
    require(q->Dequeue()==(enabled?low1:high1));
    require(q->IsEmpty() && !q->Dequeue());
  }
  auto q=CreateObject<ReportQueue>(); q->priority=true; q->SetMaxSize(QueueSize("1p"));
  require(q->Enqueue(high1) && !q->Enqueue(high2) && !q->Enqueue(low1));
  require(q->GetNPackets()==1 && q->Dequeue()==high1);
  std::cout<<"QUEUE_SELF_TEST_PASS checks="<<checks<<"\n"; return 0;
}
} }

namespace ns3 {
namespace ifapilot {
using namespace ndn;
double Now() { return Simulator::Now().GetSeconds(); }
std::ofstream packetAudit, drops, pitProbe;
void QueueDrop(std::string from, std::string to, Ptr<const Packet> p) {
  drops<<Now()<<','<<from<<','<<to<<','<<p->GetUid()<<','<<p->GetSize()<<'\n';
}
void Probe(std::map<std::string,Ptr<Node>> nodes, double step, double stop) {
  for(const auto& x:nodes) {
    if(x.first[0]=='R' || x.first=="P")
      pitProbe<<Now()<<','<<x.first<<','<<x.second->GetObject<L3Protocol>()->getForwarder()->getPit().size()<<'\n';
  }
  if(Now()+step<=stop+1e-8) Simulator::Schedule(Seconds(step),&Probe,nodes,step,stop);
}
void TraceI(std::string node, std::string event, const Interest& p, const Face& f) {
  packetAudit << Now()<<','<<node<<','<<event<<','<<f.getId()<<','<<p.getName()<<",0,"<<p.wireEncode().size()<<'\n';
}
void TraceD(std::string node, std::string event, const Data& p, const Face& f) {
  packetAudit << Now()<<','<<node<<','<<event<<','<<f.getId()<<','<<p.getName()<<",0,"<<p.wireEncode().size()<<'\n';
}
void TraceN(std::string node, std::string event, const lp::Nack& p, const Face& f) {
  packetAudit << Now()<<','<<node<<','<<event<<','<<f.getId()<<','<<p.getInterest().getName()<<','<<int(p.getReason())<<",0\n";
}
void AttachAudit(std::string node, const Face& face) {
  // Include internal management faces, which L3Protocol traces do not expose.
  const Face* f=&face;
  face.afterReceiveInterest.connect([node,f](const Interest& p,const nfd::EndpointId&) { TraceI(node,"inI",p,*f); });
  face.afterReceiveData.connect([node,f](const Data& p,const nfd::EndpointId&) { TraceD(node,"inD",p,*f); });
  face.afterReceiveNack.connect([node,f](const lp::Nack& p,const nfd::EndpointId&) { TraceN(node,"inN",p,*f); });
  auto link=face.getLinkService();
  link->afterSendInterest.connect([node,f](const Interest& p) { TraceI(node,"outI",p,*f); });
  link->afterSendData.connect([node,f](const Data& p) { TraceD(node,"outD",p,*f); });
  link->afterSendNack.connect([node,f](const lp::Nack& p) { TraceN(node,"outN",p,*f); });
}

class Service : public App {
public:
  static TypeId GetTypeId() { static TypeId t=TypeId("ns3::ifapilot::Service").SetParent<App>().AddConstructor<Service>(); return t; }
  std::string prefix, router;
  bool agent=false, silent=false;
  uint32_t payload=512, windows=10, sequence=0;
  uint32_t freshnessMs=1000;
  double interval=1;
  std::ofstream log;
  std::map<uint32_t,std::string> reports;
  std::vector<uint64_t> previous;
  std::vector<uint64_t> Read() {
    auto f=GetNode()->GetObject<L3Protocol>()->getForwarder();
    const auto& c=f->getCounters();
    return {uint64_t(c.nInInterests),uint64_t(c.nOutInterests),uint64_t(c.nInData),uint64_t(c.nOutData),
            uint64_t(c.nInNacks),uint64_t(c.nOutNacks),uint64_t(c.nSatisfiedInterests),
            uint64_t(c.nUnsatisfiedInterests),uint64_t(c.nCsHits),uint64_t(c.nCsMisses)};
  }
  void StartApplication() override {
    App::StartApplication();
    FibHelper::AddRoute(GetNode(),Name(prefix),m_face,0);
    if(agent) {
      previous=Read();
      packetAudit<<Now()<<','<<router<<",sampleBoundary,-1,"<<prefix<<"/0,0,0\n";
      Simulator::Schedule(Seconds(interval),&Service::Sample,this);
    }
  }
  void Sample() {
    auto current=Read();
    std::ostringstream s;
    s<<std::setprecision(12)<<router<<';'<<++sequence<<';'<<Now()-interval<<';'<<Now()<<';'<<Now();
    for(size_t i=0;i<current.size();++i) s<<';'<<current[i]-previous[i];
    auto f=GetNode()->GetObject<L3Protocol>()->getForwarder();
    s<<';'<<f->getPit().size();
    reports[sequence]=s.str(); previous=current;
    packetAudit<<Now()<<','<<router<<",sampleBoundary,-1,"<<prefix<<'/'<<sequence<<",0,0\n";
    log<<Now()<<",sample,"<<prefix<<'/'<<sequence<<','<<s.str()<<'\n';
    if(sequence<windows) Simulator::Schedule(Seconds(interval),&Service::Sample,this);
  }
  void OnInterest(shared_ptr<const Interest> interest) override {
    App::OnInterest(interest);
    if(!m_active) return;
    if(silent) { log<<Now()<<",receive,"<<interest->getName()<<",no_data_by_design\n"; return; }
    std::string name=interest->getName().toUri(), content;
    if(agent) {
      auto seq=std::stoul(interest->getName().at(-1).toUri());
      auto it=reports.find(seq);
      if(it==reports.end()) { log<<Now()<<",not_ready,"<<name<<",\n"; return; }
      content=it->second;
    } else content=std::string(payload,'b');
    auto data=make_shared<Data>(interest->getName());
    data->setFreshnessPeriod(::ndn::time::milliseconds(freshnessMs));
    data->setContent(make_shared<::ndn::Buffer>(content.begin(),content.end()));
    data->setSignatureInfo(SignatureInfo(static_cast<::ndn::tlv::SignatureTypeValue>(255)));
    data->setSignatureValue(make_shared<::ndn::Buffer>(1,0));
    data->wireEncode();
    log<<Now()<<",reply,"<<name<<','<<content.size()<<'\n';
    m_transmittedDatas(data,this,m_face); m_appLink->onReceiveData(*data);
  }
};
NS_OBJECT_ENSURE_REGISTERED(Service);

class Requester : public App {
public:
  static TypeId GetTypeId() { static TypeId t=TypeId("ns3::ifapilot::Requester").SetParent<App>().AddConstructor<Requester>(); return t; }
  bool collector=false;
  std::string prefix;
  double frequency=5, begin=2, end=12, interval=1, offset=.05, lifetime=1, deadline=.25;
  uint32_t windows=10, seq=0;
  std::vector<double> requestTimes; // Optional background-only fixed-demand realization.
  int64_t stream=1;
  Ptr<UniformRandomVariable> random;
  struct Pending { double request; bool done=false; };
  std::map<std::string,Pending> pending;
  std::ofstream events, received;
  void StartApplication() override {
    App::StartApplication(); random=CreateObject<UniformRandomVariable>(); random->SetStream(stream);
    if(collector) {
      for(uint32_t s=1;s<=windows;++s) for(uint32_t r=1;r<=10;++r) {
        std::string name=prefix+"/R"+std::to_string(r)+"/"+std::to_string(s);
        Simulator::Schedule(Seconds(s*interval+offset+(r-1)*.001),&Requester::Send,this,name);
      }
    } else Simulator::Schedule(Seconds(requestTimes.empty()?begin:requestTimes.front()),&Requester::Next,this);
  }
  void Next() {
    if(Now()+1e-8>=end) return;
    Send(prefix+"/"+std::to_string(++seq));
    if(!requestTimes.empty()) {
      if(seq<requestTimes.size()) Simulator::Schedule(Seconds(requestTimes[seq])-Simulator::Now(),&Requester::Next,this);
    } else Simulator::Schedule(Seconds(begin+seq/frequency)-Simulator::Now(),&Requester::Next,this);
  }
  void Send(std::string name) {
    if(!m_active) return;
    auto interest=make_shared<Interest>(Name(name));
    interest->setNonce(random->GetInteger(0,UINT32_MAX));
    interest->setCanBePrefix(false); interest->setMustBeFresh(true);
    interest->setInterestLifetime(::ndn::time::milliseconds(int64_t(lifetime*1000)));
    pending[name]={Now(),false};
    events<<Now()<<",request,"<<name<<",\n";
    m_transmittedInterests(interest,this,m_face); m_appLink->onReceiveInterest(*interest);
    Simulator::Schedule(Seconds(lifetime),&Requester::Expire,this,name);
  }
  void Expire(std::string name) {
    auto& p=pending.at(name);
    if(!p.done) { events<<Now()<<",timeout,"<<name<<",\n"; p.done=true; }
  }
  void OnData(shared_ptr<const Data> data) override {
    App::OnData(data);
    std::string name=data->getName().toUri(); auto it=pending.find(name);
    if(it==pending.end()) { events<<Now()<<",unsolicited,"<<name<<",\n"; return; }
    if(it->second.done) { events<<Now()<<",after_terminal,"<<name<<",\n"; return; }
    it->second.done=true;
    const auto& b=data->getContent();
    std::string content(reinterpret_cast<const char*>(b.value()),b.value_size());
    events<<Now()<<",data,"<<name<<','<<b.value_size()<<'\n';
    if(collector) {
      // Parse only the payload that arrived on this application's NDN face.
      std::stringstream ss(content); std::string item; std::vector<std::string> v;
      while(std::getline(ss,item,';')) v.push_back(item);
      if(v.size()!=16) { events<<Now()<<",malformed,"<<name<<",\n"; return; }
      double windowEnd=std::stod(v[3]), ready=std::stod(v[4]);
      received<<name<<','<<it->second.request<<','<<Now()<<','
              <<(Now()<=windowEnd+deadline?"on_time":"late")<<','<<content<<'\n';
      onlinebridge::Emit("R",name+"|"+content);
      if(ready>Now()) events<<Now()<<",future_payload,"<<name<<",\n";
    }
  }
  void OnNack(shared_ptr<const lp::Nack> nack) override {
    App::OnNack(nack); auto name=nack->getInterest().getName().toUri();
    auto it=pending.find(name); if(it!=pending.end()) it->second.done=true;
    events<<Now()<<",nack,"<<name<<','<<int(nack->getReason())<<'\n';
  }
};
NS_OBJECT_ENSURE_REGISTERED(Requester);

int Run(int argc,char** argv) {
  std::string config="config/benign-ifapilot.json",out="runs/benign-tree-s1-r1";
  bool queueSelfTest=false;
  CommandLine cmd; cmd.AddValue("queueSelfTest","Exercise wire classifier and admission/service policy",queueSelfTest); cmd.AddValue("config","Pilot JSON",config); cmd.AddValue("out","Existing output directory",out); cmd.Parse(argc,argv);
  if(queueSelfTest) return QueueSelfTest();
  boost::property_tree::ptree c; boost::property_tree::read_json(config,c);

  if(c.get<uint32_t>("report_retransmissions")!=0) throw std::runtime_error("This ifapilot implements zero retransmissions");
  GlobalValue::Bind("SimulatorImplementationType",StringValue("ns3::RealtimeSimulatorImpl"));
  onlinebridge::Init(c.get<std::string>("online_socket"));
  RngSeedManager::SetSeed(c.get<uint32_t>("seed")); RngSeedManager::SetRun(c.get<uint64_t>("rngRun"));
  std::map<std::string,Ptr<Node>> nodes;
  std::ofstream layout(out+"/nodes.csv"); layout<<"name,node_id,role\n";
  for(const auto& x:c.get_child("routers")) {
    std::string n=x.second.get_value<std::string>(); nodes[n]=CreateObject<Node>(); Names::Add(n,nodes[n]);
    layout<<n<<','<<nodes[n]->GetId()<<",router\n";
  }
  for(const auto& x:c.get_child("endpoints")) {
    nodes[x.first]=CreateObject<Node>(); Names::Add(x.first,nodes[x.first]);
    layout<<x.first<<','<<nodes[x.first]->GetId()<<','<<x.second.get_value<std::string>()<<'\n';
  }
  Config::SetDefault("ns3::PointToPointNetDevice::DataRate",StringValue(c.get<std::string>("bandwidth")));
  Config::SetDefault("ns3::PointToPointChannel::Delay",StringValue(c.get<std::string>("delay")));
  Config::SetDefault("ns3::DropTailQueue<Packet>::MaxSize",StringValue(c.get<std::string>("queue")));
  const std::string mode=c.get<std::string>("monitor_transport","fifo");
  if(mode!="fifo" && mode!="priority") throw std::runtime_error("Invalid monitor_transport");
  if(c.get<std::string>("queue")!="100p") throw std::runtime_error("Requires shared 100p buffer");
  priorityPrefix="/report/"+c.get<std::string>("runId");
  priorityWindows=c.get<uint32_t>("report_windows");
  queueAudit.open(out+"/queue-policy.csv");
  queueAudit<<"time,from,to,event,packet_uid,bytes,type,name,report_class,queued_after\n";
  wireAudit.open(out+"/bottleneck-wire.csv");
  wireAudit<<"time,from,to,event,packet_uid,bytes,type,name,report_class\n";
  PointToPointHelper p2p;
  struct Link { std::string a,b; NetDeviceContainer devices; }; std::vector<Link> links;
  for(const auto& x:c.get_child("links")) {
    auto it=x.second.begin(); std::string a=(it++)->second.get_value<std::string>(),b=it->second.get_value<std::string>();
    auto devices=p2p.Install(nodes.at(a),nodes.at(b));
    if((a=="R8" && b=="R10") || (a=="R10" && b=="R8")) {
      for(uint32_t i=0;i<2;++i) {
        auto dev=DynamicCast<PointToPointNetDevice>(devices.Get(i));
        auto q=CreateObject<ReportQueue>(); q->SetMaxSize(QueueSize("100p"));
        q->priority=(mode=="priority"); q->from=(i==0?a:b); q->to=(i==0?b:a);
        dev->SetQueue(q);
        dev->TraceConnectWithoutContext("PhyTxBegin",MakeBoundCallback(&WireTrace,q->from,q->to,std::string("tx_begin")));
        dev->TraceConnectWithoutContext("PhyTxEnd",MakeBoundCallback(&WireTrace,q->from,q->to,std::string("tx_end")));
      }
    }
    links.push_back({a,b,devices});
  }
  StackHelper stack; stack.setCsSize(c.get<uint32_t>("cs_packets")); stack.InstallAll();
  StrategyChoiceHelper::InstallAll("/","/localhost/nfd/strategy/best-route");
  GlobalRoutingHelper routing; routing.InstallAll();
  std::ofstream faces(out+"/links.csv"); faces<<"a,b,a_face,b_face,a_bps,b_bps,delay_s,a_queue,b_queue\n";
  drops.open(out+"/queue-drops.csv"); drops<<std::setprecision(12)<<"time,from,to,packet_uid,bytes\n";
  pitProbe.open(out+"/pit-probe.csv"); pitProbe<<std::setprecision(12)<<"time,node,entries\n";
  for(const auto& l:links) {
    auto da=DynamicCast<PointToPointNetDevice>(l.devices.Get(0)), db=DynamicCast<PointToPointNetDevice>(l.devices.Get(1));
    const auto limited=c.get<std::string>("monitor_bottleneck_bps","");
    if(!limited.empty() &&
       ((l.a=="R8" && l.b=="R10") ||
        (l.a=="R10" && l.b=="R8"))) {
      auto tx=(l.a=="R8"?da:db);
      tx->SetAttribute("DataRate",StringValue(limited));
    }
    da->GetQueue()->TraceConnectWithoutContext("Drop",MakeBoundCallback(&QueueDrop,l.a,l.b));
    db->GetQueue()->TraceConnectWithoutContext("Drop",MakeBoundCallback(&QueueDrop,l.b,l.a));
    DataRateValue ra,rb; TimeValue delay;
    da->GetAttribute("DataRate",ra); db->GetAttribute("DataRate",rb); da->GetChannel()->GetAttribute("Delay",delay);
    faces<<l.a<<','<<l.b<<','
      <<nodes[l.a]->GetObject<L3Protocol>()->getFaceByNetDevice(da)->getId()<<','
      <<nodes[l.b]->GetObject<L3Protocol>()->getFaceByNetDevice(db)->getId()<<','
      <<ra.Get().GetBitRate()<<','<<rb.Get().GetBitRate()<<','<<delay.Get().GetSeconds()<<','
      <<da->GetQueue()->GetMaxSize()<<','<<db->GetQueue()->GetMaxSize()<<'\n';
  }
  std::ofstream cache(out+"/cache-limits.csv"); cache<<"node,packet_limit\n";
  for(const auto& x:nodes) cache<<x.first<<','<<x.second->GetObject<L3Protocol>()->getForwarder()->getCs().getLimit()<<'\n';
  packetAudit.open(out+"/audit-packets.csv"); packetAudit<<std::setprecision(12)<<"time,node,event,face,name,reason,ndn_wire_bytes\n";
  for(auto& x:nodes) {
    auto l3=x.second->GetObject<L3Protocol>();
    for(auto& face:l3->getFaceTable()) AttachAudit(x.first,face);
    std::string node=x.first;
    l3->getFaceTable().afterAdd.connect([node](const Face& face) { AttachAudit(node,face); });
  }
  const std::string run=c.get<std::string>("runId"), benign="/benign/"+run, report="/report/"+run, background="/background/"+run;
  std::vector<Ptr<Service>> services;
  auto producer=CreateObject<Service>(); producer->prefix=benign; producer->payload=c.get<uint32_t>("consumer_payload_bytes");
  producer->freshnessMs=c.get<uint32_t>("data_freshness_ms");
  producer->log.open(out+"/producer.csv"); producer->log<<std::setprecision(12)<<"time,event,name,detail\n";
  nodes.at("P")->AddApplication(producer); producer->SetStartTime(Seconds(0)); services.push_back(producer);
  routing.AddOrigins(benign,nodes.at("P"));
  auto bgProducer=CreateObject<Service>();
  bgProducer->prefix=background;
  bgProducer->payload=c.get<uint32_t>("consumer_payload_bytes");
  bgProducer->freshnessMs=c.get<uint32_t>("data_freshness_ms");
  bgProducer->log.open(out+"/background-producer.csv");
  bgProducer->log<<std::setprecision(12)<<"time,event,name,detail\n";
  nodes.at("R8")->AddApplication(bgProducer);
  bgProducer->SetStartTime(Seconds(0));
  services.push_back(bgProducer);
  routing.AddOrigins(background,nodes.at("R8"));
  auto sink=CreateObject<Service>(); sink->silent=true; sink->prefix="/ifa/"+run;
  sink->log.open(out+"/sink.csv"); sink->log<<std::setprecision(12)<<"time,event,name,detail\n";
  nodes.at("P")->AddApplication(sink); sink->SetStartTime(Seconds(0)); services.push_back(sink);
  routing.AddOrigins(sink->prefix,nodes.at("P"));
  for(int r=1;r<=10;++r) {
    std::string n="R"+std::to_string(r); auto a=CreateObject<Service>(); a->agent=true; a->router=n; a->prefix=report+"/"+n;
    a->freshnessMs=c.get<uint32_t>("data_freshness_ms");
    a->interval=c.get<double>("report_interval_s"); a->windows=c.get<uint32_t>("report_windows");
    a->log.open(out+"/agent-"+n+".csv"); a->log<<std::setprecision(12)<<"time,event,name,detail\n";
    nodes.at(n)->AddApplication(a); a->SetStartTime(Seconds(0)); routing.AddOrigins(a->prefix,nodes.at(n)); services.push_back(a);
  }
  std::vector<Ptr<Requester>> clients;
  for(int i=0;i<=3;++i) {
    auto a=CreateObject<Requester>(); a->collector=(i==0); std::string node=i==0?"M":"C"+std::to_string(i);
    a->stream=i+1;
    a->prefix=i==0?report:benign+"/"+node;
    a->frequency=c.get<double>("consumer_frequency_hz"); a->begin=c.get<double>("consumer_start_s"); a->end=c.get<double>("consumer_stop_s");
    a->interval=c.get<double>("report_interval_s"); a->offset=c.get<double>("report_poll_offset_s");
    a->windows=c.get<uint32_t>("report_windows"); a->lifetime=c.get<double>("interest_lifetime_s"); a->deadline=c.get<double>("report_deadline_s");
    a->events.open(out+"/client-"+node+".csv"); a->events<<std::setprecision(12)<<"time,event,name,detail\n";
    if(a->collector) { a->received.open(out+"/collector-received.csv"); a->received<<std::setprecision(12)<<"name,request,arrival,status,payload\n"; }
    nodes.at(node)->AddApplication(a); a->SetStartTime(Seconds(0)); clients.push_back(a);
  }
  for(const auto& entry:c.get_child("extra_flows")) {
    const auto& f=entry.second;
    std::string id=f.get<std::string>("id"),node=f.get<std::string>("node"),kind=f.get<std::string>("kind");
    if(kind!="attack" && kind!="burst" && kind!="background") throw std::runtime_error("Invalid extra-flow kind");
    if(kind=="attack" && !c.get<bool>("attackers_active")) throw std::runtime_error("Attack not authorized in config");
    if(kind=="background" &&
       (node!="P" || f.get<std::string>("server_node","R8")!="R8"))
      throw std::runtime_error("Background flow must be P to R8");
    auto a=CreateObject<Requester>();
    a->prefix=(kind=="attack"?sink->prefix:
              kind=="background"?background:benign)+"/"+id;
    a->frequency=f.get<double>("frequency_hz"); a->begin=f.get<double>("start_s"); a->end=f.get<double>("stop_s");
    a->lifetime=f.get<double>("lifetime_s"); a->stream=f.get<int64_t>("rng_stream");
    if(a->frequency<=0 || a->begin<1 || a->end<=a->begin || a->end+a->lifetime+1>=c.get<double>("duration_s"))
      throw std::runtime_error("Invalid extra-flow timing/rate");
    auto schedule=f.get_child_optional("background_request_times_s");
    if(schedule) {
      if(kind!="background") throw std::runtime_error("Only background may have a sweep schedule");
      double previous=-1;
      for(const auto& value:*schedule) {
        double t=value.second.get_value<double>();
        if(!std::isfinite(t) || t<a->begin || t>=a->end || t<=previous)
          throw std::runtime_error("Invalid background schedule");
        a->requestTimes.push_back(t); previous=t;
      }
      if(a->requestTimes.empty()) throw std::runtime_error("Empty schedule is forbidden");
    }
    a->events.open(out+"/flow-"+id+".csv"); a->events<<std::setprecision(12)<<"time,event,name,detail\n";
    nodes.at(node)->AddApplication(a); a->SetStartTime(Seconds(0)); clients.push_back(a);
  }
  GlobalRoutingHelper::CalculateRoutes();
  Simulator::Schedule(Seconds(0.1),&Probe,nodes,0.1,c.get<double>("duration_s")-0.5);
  // Route dump is audit only. Never accessed by Requester/collector.
  Simulator::Schedule(Seconds(.01),[nodes,out] {
    std::ofstream fib(out+"/fib.txt"); fib<<"# simulation_time_s="<<Now()<<'\n';
    for(const auto& x:nodes) for(const auto& entry:x.second->GetObject<L3Protocol>()->getForwarder()->getFib())
      for(const auto& hop:entry.getNextHops()) fib<<x.first<<' '<<entry.getPrefix()<<" face="<<hop.getFace().getId()<<" cost="<<hop.getCost()<<'\n';
  });

  for(uint32_t seq=1;seq<=c.get<uint32_t>("report_windows");++seq)
    Simulator::Schedule(Seconds(seq*c.get<double>("report_interval_s")+c.get<double>("report_deadline_s")),&onlinebridge::Frame,seq);
  Simulator::Stop(Seconds(c.get<double>("duration_s")));
  onlinebridge::origin=onlinebridge::Mono(); onlinebridge::Emit("S",std::to_string(onlinebridge::origin));
  Simulator::Run(); onlinebridge::Emit("E",std::to_string(onlinebridge::failures));
  std::ofstream ipc(out+"/ipc.json"); ipc<<"{\"failures\":"<<onlinebridge::failures<<",\"sent\":"<<onlinebridge::sent<<",\"origin_ns\":"<<onlinebridge::origin<<"}\n";ipc.close();close(onlinebridge::fd);

  for(auto a:clients) { a->events.flush(); if(a->collector) a->received.flush(); }
  for(auto a:services) a->log.flush();
  packetAudit.flush(); drops.flush(); pitProbe.flush(); queueAudit.flush(); wireAudit.flush();
  std::cout<<"SIMULATION_COMPLETE nodes="<<nodes.size()<<" links="<<links.size()<<" scope=controlled_ifa_no_detector\n";
  Simulator::Destroy(); return 0;
}
} // namespace ifapilot
} // namespace ns3
int main(int argc,char** argv) { return ns3::ifapilot::Run(argc,argv); }
