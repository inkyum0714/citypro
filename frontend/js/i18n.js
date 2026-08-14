/** CityFlow UI i18n (ko / en). Cookie cityflow_lang is read by the server. */

const CITYFLOW_LANG_COOKIE = 'cityflow_lang';

const I18N = {
    ko: {
        'meta.title': 'CityFlow — 교통 시뮬레이션',
        'meta.login_title': 'CityFlow — 로그인',
        'meta.checkout_title': 'CityFlow — 결제',
        'meta.pay_title': 'CityFlow — 결제 결과',
        'brand.tagline': '실시간 교통 시뮬레이션',
        'weather.clear': '맑음',
        'weather.rain': '폭우',
        'weather.fog': '안개',
        'time.day': '주간',
        'time.rush_hour': '출퇴근 시간',
        'nav.honorific': '님',
        'nav.logout': '로그아웃',
        'nav.pause': '⏸ 일시정지',
        'nav.resume': '▶ 재개',
        'nav.reset': '↺ 초기화',
        'nav.pro': 'PRO',
        'nav.shop': '🪙 상점',
        'nav.lang_to_en': 'EN',
        'nav.lang_to_ko': '한국어',
        'player.streak': '{n}일',
        'section.missions': '오늘의 미션',
        'section.stages': '스테이지',
        'section.saves': '도시 저장',
        'section.skins': '스킨',
        'section.achievements': '업적',
        'section.leaderboard': '주간 랭킹',
        'section.dashboard': '대시보드',
        'section.analytics': '교통 분석',
        'section.events': '교통 이벤트',
        'metric.active_vehicles': '활성 차량',
        'metric.total_trips': '총 통행',
        'metric.roads': '도로',
        'metric.events': '이벤트',
        'metric.congestion': '혼잡도',
        'metric.throughput': '통과량/분',
        'metric.wait': '평균 대기(s)',
        'metric.peak': '최대 혼잡',
        'spawn.auto': '자동 차량 생성',
        'spawn.rate': '자동 생성 빈도',
        'spawn.type': '차량 종류',
        'spawn.random': '일반 (랜덤)',
        'spawn.car': '승용차',
        'spawn.truck': '트럭',
        'spawn.bus': '버스',
        'spawn.emergency': '긴급차',
        'spawn.one': '차량 1대 생성 (도로 시작)',
        'spawn.hint': '하단 도구에서 <strong>차량 배치</strong>를 선택한 뒤 도로를 클릭해도 됩니다.',
        'save.slot': '슬롯 {n}',
        'save.slot_named': '슬롯 {n}: {name}',
        'save.slot_empty': '슬롯 {n} (비어 있음)',
        'save.placeholder': '도시 이름',
        'save.save': '저장',
        'save.load': '불러오기',
        'loading': '불러오는 중…',
        'export.csv': 'CSV 내보내기',
        'ad.label': '스폰서',
        'ad.body': '교통 시뮬레이션을 즐기는 중입니다',
        'ad.cta': '광고 제거 · PRO',
        'ad.top_label': '광고',
        'ad.family_safe': '가족 안심 · 성인 광고 없음',
        'ad.house_title': '광고 없이 더 크게 달리세요',
        'ad.house_body': 'PRO로 상단 광고를 끄고 VIP 이벤트·CSV를 쓰세요. 결제는 토스페이먼츠로 정산됩니다.',
        'ad.house_cta': 'PRO 시작',
        'camera.zoom_in': '확대',
        'camera.zoom_out': '축소',
        'camera.fit': '전체 보기',
        'camera.reset': '줌 리셋',
        'canvas.hint': '캔버스를 드래그하여 도로를 건설하세요 · 휠 줌 · 우클릭 이동',
        'events.desc': '도로 위 상황을 유발하거나 자동 이벤트를 관찰하세요.',
        'events.rescue': '사고 대응',
        'events.rescue_desc': '충돌 차량은 질량·위치 기반 작용-반작용으로 튕깁니다. 아래 버튼으로 현장을 해결하세요.',
        'events.police': '🚓 경찰 출동',
        'events.tow': '🚛 견인차',
        'events.clear_now': '✅ 즉시 정리',
        'events.clear_all': '모든 이벤트 해제',
        'events.active': '활성 이벤트',
        'events.log': '이벤트 로그',
        'events.empty': '현재 이벤트 없음',
        'events.start': '시뮬레이션을 시작하세요',
        'events.none_logged': '아직 기록된 이벤트가 없습니다',
        'events.remaining': '남은 시간 {s}s',
        'events.occurred': '{label} 발생',
        'events.manual': '{label} 수동 발생',
        'accidents.status': '사고 현장: {n}건',
        'accidents.tow': '견인',
        'accidents.police': '경찰',
        'accidents.eta': ' · {label} ETA {eta}s',
        'tool.road': '🛣️ 도로 건설',
        'tool.spawn': '🚗 차량 배치',
        'tool.bus_stop': '🚌 정류장',
        'tool.inspect': '🔍 관찰',
        'road.lanes': '차선',
        'road.lanes_title': '생성할 도로의 차선 수',
        'road.bidirectional': '왕복',
        'cargo.label': '화물 분류:',
        'cargo.food': '식품',
        'cargo.construction': '건설자재',
        'cargo.fuel': '연료',
        'cargo.general': '일반화물',
        'status.connecting': '서버 연결 중...',
        'status.paused': '시뮬레이션이 일시정지되었습니다.',
        'status.running': '실시간 운행 중 · 차량 {n}대',
        'status.connected': '서버 연결 완료',
        'shop.title': '🪙 City 코인 상점',
        'shop.desc': '플레이로 모은 코인으로 부스터·스킨·저장 슬롯을 구매하세요.',
        'shop.owned': '보유 중',
        'pro.title': 'CityFlow 멤버십',
        'pro.coupon_label': '레딧 무료체험 쿠폰 (영문·숫자 8자리)',
        'pro.coupon_apply': '적용',
        'pro.coupon_desc': '계정당 1회, 선착순 10명, PRO 7일 체험. 코드 예: RDT1WEEK',
        'pro.current': '이용 중',
        'pro.pay': '{price} 결제',
        'pro.pay_setup': '결제 설정 필요',
        'pro.toss': '토스 결제',
        'coupon.trial_expired': '무료 체험이 만료되었습니다.',
        'login.sub': '교통 시뮬레이션에 로그인하세요',
        'login.id': '로그인 ID',
        'login.password': '비밀번호',
        'login.submit': '로그인',
        'login.register': '회원가입',
        'login.name': '이름',
        'login.password_hint': '비밀번호 (8자 이상)',
        'login.signup': '가입하기',
        'login.google': 'Google로 계속하기',
        'login.google_note': 'Google 로그인: all_variable.json의 auth.google_client_id / secret 설정 후 google_enabled를 true로 변경하세요.',
        'login.fail': '로그인 실패',
        'login.network': '네트워크 오류가 발생했습니다.',
        'login.parse': '서버 응답을 해석할 수 없습니다.',
        'checkout.title': 'CityFlow 결제',
        'checkout.pay': '토스로 결제하기',
        'checkout.note': '결제 완료 후 등록하신 토스페이먼츠 정산 계좌로 입금됩니다.',
        'checkout.back': '돌아가기',
        'checkout.cancel': '취소하고 돌아가기',
        'checkout.open_fail': '결제창을 열 수 없습니다.',
        'pay.ok': '결제 완료',
        'pay.fail': '결제 실패',
        'pay.until': '{plan} · {date}까지',
        'pay.back': '시뮬레이션으로 돌아가기',
        'toast.connected': 'CityFlow 서버에 연결되었습니다.',
        'toast.conn_error': '연결 오류',
        'toast.ws_lost': '실시간 연결이 끊어졌습니다. REST로 동기화합니다.',
        'toast.ws_error': 'WebSocket 연결 오류 — REST 모드',
        'toast.no_server': '서버와 연결되지 않았습니다.',
        'toast.road_short': '도로가 너무 짧습니다. 조금 더 길게 드래그하세요.',
        'toast.reset_confirm': '도로와 차량, 이벤트를 모두 초기화할까요?',
        'toast.csv_pro': 'CSV 내보내기는 PRO 기능입니다. PRO를 체험해 보세요.',
        'chart.collecting': '데이터 수집 중…',
        'stage.clear': '클리어',
        'stage.active': '진행 중',
        'stage.start': '시작',
        'stage.load_fail': '스테이지 로드 실패',
        'stage.already': '이미 클리어',
        'stage.claim': '클리어 보상 받기',
        'quest.loading': '퀘스트 로딩 중…',
        'quest.claim': '보상',
        'quest.bonus_claimed': '오늘 보너스 수령함',
        'quest.bonus': '일일 올클리어 보너스 (+100🪙)',
        'ach.empty': '업적 정보 없음',
        'lb.weekly': '주간 XP {n}',
        'lb.empty': '아직 참가자가 없습니다',
        'inspect.unclassified': ' · 화물 미분류',
        'inspect.cargo': ' · 화물 {type}',
        'inspect.dwell': ' · 정류장 정차중',
        'inspect.volume': '부피',
        'inspect.occupancy': '점유',
        'cosmetic.default': '기본',
        'cosmetic.neon': '네온',
        'cosmetic.sunset': '선셋',
        'event.accident.label': '교통사고',
        'event.construction.label': '공사 구간',
        'event.traffic_jam.label': '정체',
        'event.rush_hour.label': '출퇴근 러시아워',
        'event.rain.label': '폭우',
        'event.fog.label': '안개',
        'event.vip_convoy.label': 'VIP 호송',
        'event.police_response.label': '경찰 출동',
        'event.tow_truck.label': '견인차 출동',
        'event.clear_accident.label': '사고 현장 정리',
        'quest.build_roads.label': '도로 건설',
        'quest.build_roads.desc': '도로 3개 건설',
        'quest.move_traffic.label': '교통 흐름',
        'quest.move_traffic.desc': '완주 15회 달성',
        'quest.golden_hour.label': '골든 아워',
        'quest.golden_hour.desc': '원활한 흐름(평균속도↑) 40초 유지',
        'quest.accident_cleanup.label': '사고 클린업',
        'quest.accident_cleanup.desc': '교통사고 2건 정리(경찰/견인)',
        'quest.bus_stops.label': '버스 정류장',
        'quest.bus_stops.desc': '정류장 2개 개설',
        'quest.cargo_sort.label': '화물 분류',
        'quest.cargo_sort.desc': '트럭 화물 3건 분류',
        'shop.booster_xp_1h.name': 'XP 부스터 (1시간)',
        'shop.booster_xp_1h.desc': '획득 XP 1.5배',
        'shop.cosmetic_neon.name': '네온 도로 스킨',
        'shop.cosmetic_neon.desc': '도로·차량 네온 테마',
        'shop.cosmetic_sunset.name': '선셋 스킨',
        'shop.cosmetic_sunset.desc': '따뜻한 저녁 톤 UI',
        'shop.save_slot_extra.name': '도시 저장 슬롯 +1',
        'shop.save_slot_extra.desc': '영구 저장 공간 확장',
        'ach.first_road': '첫 도로',
        'ach.mayor': '도시 설계자',
        'ach.traffic_master': '교통 마스터',
        'ach.week_warrior': '7일 연속 접속',
        'ach.bus_network': '버스 노선왕',
        'ach.cargo_master': '물류 마스터',
        'ach.golden_keeper': '골든 키퍼',
        'ach.rescue_hero': '구조 영웅',
        'ach.stage_clearer': '스테이지 클리어',
        'stage.stage_01_first_flow.name': '스테이지 1 · 첫 흐름',
        'stage.stage_01_first_flow.desc': 'L자 도로에서 차량 5대가 목적지에 도착하세요.',
        'stage.stage_02_junction.name': '스테이지 2 · 교차로 구축',
        'stage.stage_02_junction.desc': '십자 도로를 확장하고, 버스 정류장 1개를 세우세요.',
        'stage.stage_03_cargo_line.name': '스테이지 3 · 화물 노선',
        'stage.stage_03_cargo_line.desc': '트럭 화물을 분류하고 골든 아워를 유지하세요.',
        'stage.stage_04_rescue.name': '스테이지 4 · 구조 작전',
        'stage.stage_04_rescue.desc': '혼잡한 도시에서 사고를 정리하고 정류장을 운영하세요.',
        'goal.trips_completed': '완주 {n}회',
        'goal.roads_built': '도로 {n}개 추가',
        'goal.bus_stops_built': '정류장 {n}개',
        'goal.cargo_classified': '화물 분류 {n}건',
        'goal.golden_flow_seconds': '골든 흐름 {n}초',
        'goal.accidents_cleared': '사고 정리 {n}건',
        'plan.price_usd': '${usd}/월',
        'plan.price_krw': '₩{krw}',
        'plan.pro.b0': '광고 제거',
        'plan.pro.b1': '도시 저장 5슬롯',
        'plan.pro.b2': 'VIP 이벤트 · CSV 내보내기',
        'plan.pro.b3': '일일 코인 2배 · XP 1.25배',
        'plan.pro_plus.b0': 'PRO 모든 혜택',
        'plan.pro_plus.b1': '도시 저장 10슬롯',
        'plan.pro_plus.b2': 'XP 1.5배',
        'plan.ultra.b0': 'PRO+ 모든 혜택',
        'plan.ultra.b1': '도시 저장 20슬롯',
        'plan.ultra.b2': '일일 코인 3배 · XP 2배',
        'canvas.golden': '골든 아워 {s}s · 평균 {avg}',
        'canvas.hud': '줌 {zoom}% · 휠 확대/축소 · 우클릭/관찰 모드 드래그 이동',
    },
    en: {
        'meta.title': 'CityFlow — Traffic Simulation',
        'meta.login_title': 'CityFlow — Sign in',
        'meta.checkout_title': 'CityFlow — Checkout',
        'meta.pay_title': 'CityFlow — Payment result',
        'brand.tagline': 'Real-time traffic simulation',
        'weather.clear': 'Clear',
        'weather.rain': 'Heavy rain',
        'weather.fog': 'Fog',
        'time.day': 'Daytime',
        'time.rush_hour': 'Rush hour',
        'nav.honorific': '',
        'nav.logout': 'Sign out',
        'nav.pause': '⏸ Pause',
        'nav.resume': '▶ Resume',
        'nav.reset': '↺ Reset',
        'nav.pro': 'PRO',
        'nav.shop': '🪙 Shop',
        'nav.lang_to_en': 'EN',
        'nav.lang_to_ko': '한국어',
        'player.streak': '{n}d',
        'section.missions': "Today's missions",
        'section.stages': 'Stages',
        'section.saves': 'City saves',
        'section.skins': 'Skins',
        'section.achievements': 'Achievements',
        'section.leaderboard': 'Weekly ranking',
        'section.dashboard': 'Dashboard',
        'section.analytics': 'Traffic analytics',
        'section.events': 'Traffic events',
        'metric.active_vehicles': 'Active vehicles',
        'metric.total_trips': 'Trips completed',
        'metric.roads': 'Roads',
        'metric.events': 'Events',
        'metric.congestion': 'Congestion',
        'metric.throughput': 'Throughput/min',
        'metric.wait': 'Avg wait (s)',
        'metric.peak': 'Peak congestion',
        'spawn.auto': 'Auto-spawn vehicles',
        'spawn.rate': 'Spawn rate',
        'spawn.type': 'Vehicle type',
        'spawn.random': 'Standard (random)',
        'spawn.car': 'Car',
        'spawn.truck': 'Truck',
        'spawn.bus': 'Bus',
        'spawn.emergency': 'Emergency',
        'spawn.one': 'Spawn 1 vehicle (road start)',
        'spawn.hint': 'You can also select <strong>Place vehicle</strong> below and click a road.',
        'save.slot': 'Slot {n}',
        'save.slot_named': 'Slot {n}: {name}',
        'save.slot_empty': 'Slot {n} (empty)',
        'save.placeholder': 'City name',
        'save.save': 'Save',
        'save.load': 'Load',
        'loading': 'Loading…',
        'export.csv': 'Export CSV',
        'ad.label': 'Sponsored',
        'ad.body': 'Enjoying traffic simulation',
        'ad.cta': 'Remove ads · PRO',
        'ad.top_label': 'Ad',
        'ad.family_safe': 'Family-safe · no adult ads',
        'ad.house_title': 'Go bigger without ads',
        'ad.house_body': 'PRO removes the top banner and unlocks VIP events and CSV. Payouts settle through Toss Payments.',
        'ad.house_cta': 'Get PRO',
        'camera.zoom_in': 'Zoom in',
        'camera.zoom_out': 'Zoom out',
        'camera.fit': 'Fit view',
        'camera.reset': 'Reset zoom',
        'canvas.hint': 'Drag on the canvas to build roads · wheel zoom · right-click pan',
        'events.desc': 'Trigger road incidents or watch automatic events.',
        'events.rescue': 'Accident response',
        'events.rescue_desc': 'Crashed vehicles bounce with mass-based reaction. Use the buttons below to clear the scene.',
        'events.police': '🚓 Dispatch police',
        'events.tow': '🚛 Tow truck',
        'events.clear_now': '✅ Clear now',
        'events.clear_all': 'Clear all events',
        'events.active': 'Active events',
        'events.log': 'Event log',
        'events.empty': 'No active events',
        'events.start': 'Start the simulation',
        'events.none_logged': 'No events logged yet',
        'events.remaining': '{s}s remaining',
        'events.occurred': '{label} started',
        'events.manual': '{label} triggered',
        'accidents.status': 'Accident scenes: {n}',
        'accidents.tow': 'Tow',
        'accidents.police': 'Police',
        'accidents.eta': ' · {label} ETA {eta}s',
        'tool.road': '🛣️ Build road',
        'tool.spawn': '🚗 Place vehicle',
        'tool.bus_stop': '🚌 Bus stop',
        'tool.inspect': '🔍 Inspect',
        'road.lanes': 'Lanes',
        'road.lanes_title': 'Number of lanes for new roads',
        'road.bidirectional': 'Two-way',
        'cargo.label': 'Cargo class:',
        'cargo.food': 'Food',
        'cargo.construction': 'Construction',
        'cargo.fuel': 'Fuel',
        'cargo.general': 'General',
        'status.connecting': 'Connecting to server...',
        'status.paused': 'Simulation paused.',
        'status.running': 'Live · {n} vehicles',
        'status.connected': 'Server connected',
        'shop.title': '🪙 City coin shop',
        'shop.desc': 'Spend coins from play on boosters, skins, and save slots.',
        'shop.owned': 'Owned',
        'pro.title': 'CityFlow membership',
        'pro.coupon_label': 'Reddit free-trial coupon (8 letters or numbers)',
        'pro.coupon_apply': 'Apply',
        'pro.coupon_desc': 'Once per account, first 10 people, 7-day PRO trial. Example: RDT1WEEK',
        'pro.current': 'Current',
        'pro.pay': 'Pay {price}',
        'pro.pay_setup': 'Payments not configured',
        'pro.toss': 'Toss Payments',
        'coupon.trial_expired': 'Your free trial has expired.',
        'login.sub': 'Sign in to the traffic simulation',
        'login.id': 'Login ID',
        'login.password': 'Password',
        'login.submit': 'Sign in',
        'login.register': 'Create account',
        'login.name': 'Name',
        'login.password_hint': 'Password (8+ characters)',
        'login.signup': 'Sign up',
        'login.google': 'Continue with Google',
        'login.google_note': 'Google sign-in: set auth.google_client_id / secret in all_variable.json, then set google_enabled to true.',
        'login.fail': 'Sign-in failed',
        'login.network': 'A network error occurred.',
        'login.parse': 'Could not parse the server response.',
        'checkout.title': 'CityFlow checkout',
        'checkout.pay': 'Pay with Toss',
        'checkout.note': 'After payment, funds go to your registered Toss Payments settlement account.',
        'checkout.back': 'Go back',
        'checkout.cancel': 'Cancel and go back',
        'checkout.open_fail': 'Could not open the payment window.',
        'pay.ok': 'Payment complete',
        'pay.fail': 'Payment failed',
        'pay.until': '{plan} · until {date}',
        'pay.back': 'Back to simulation',
        'toast.connected': 'Connected to CityFlow.',
        'toast.conn_error': 'Connection error',
        'toast.ws_lost': 'Live connection lost. Syncing over REST.',
        'toast.ws_error': 'WebSocket error — REST mode',
        'toast.no_server': 'Not connected to the server.',
        'toast.road_short': 'Road is too short. Drag a little farther.',
        'toast.reset_confirm': 'Reset all roads, vehicles, and events?',
        'toast.csv_pro': 'CSV export is a PRO feature. Try PRO.',
        'chart.collecting': 'Collecting data…',
        'stage.clear': 'Cleared',
        'stage.active': 'In progress',
        'stage.start': 'Start',
        'stage.load_fail': 'Failed to load stages',
        'stage.already': 'Already cleared',
        'stage.claim': 'Claim clear reward',
        'quest.loading': 'Loading quests…',
        'quest.claim': 'Claim',
        'quest.bonus_claimed': "Today's bonus claimed",
        'quest.bonus': 'Daily all-clear bonus (+100🪙)',
        'ach.empty': 'No achievement data',
        'lb.weekly': 'Weekly XP {n}',
        'lb.empty': 'No participants yet',
        'inspect.unclassified': ' · cargo unclassified',
        'inspect.cargo': ' · cargo {type}',
        'inspect.dwell': ' · dwelling at stop',
        'inspect.volume': 'vol',
        'inspect.occupancy': 'occ',
        'cosmetic.default': 'Default',
        'cosmetic.neon': 'Neon',
        'cosmetic.sunset': 'Sunset',
        'event.accident.label': 'Accident',
        'event.construction.label': 'Construction',
        'event.traffic_jam.label': 'Traffic jam',
        'event.rush_hour.label': 'Rush hour',
        'event.rain.label': 'Heavy rain',
        'event.fog.label': 'Fog',
        'event.vip_convoy.label': 'VIP convoy',
        'event.police_response.label': 'Police response',
        'event.tow_truck.label': 'Tow truck',
        'event.clear_accident.label': 'Clear accident',
        'quest.build_roads.label': 'Build roads',
        'quest.build_roads.desc': 'Build 3 roads',
        'quest.move_traffic.label': 'Traffic flow',
        'quest.move_traffic.desc': 'Complete 15 trips',
        'quest.golden_hour.label': 'Golden hour',
        'quest.golden_hour.desc': 'Keep smooth flow (higher avg speed) for 40 seconds',
        'quest.accident_cleanup.label': 'Accident cleanup',
        'quest.accident_cleanup.desc': 'Clear 2 accidents (police/tow)',
        'quest.bus_stops.label': 'Bus stops',
        'quest.bus_stops.desc': 'Place 2 bus stops',
        'quest.cargo_sort.label': 'Cargo sorting',
        'quest.cargo_sort.desc': 'Classify 3 truck cargo loads',
        'shop.booster_xp_1h.name': 'XP booster (1 hour)',
        'shop.booster_xp_1h.desc': '1.5× XP earned',
        'shop.cosmetic_neon.name': 'Neon road skin',
        'shop.cosmetic_neon.desc': 'Neon theme for roads and vehicles',
        'shop.cosmetic_sunset.name': 'Sunset skin',
        'shop.cosmetic_sunset.desc': 'Warm evening UI tones',
        'shop.save_slot_extra.name': 'City save slot +1',
        'shop.save_slot_extra.desc': 'Permanent extra save space',
        'ach.first_road': 'First road',
        'ach.mayor': 'City planner',
        'ach.traffic_master': 'Traffic master',
        'ach.week_warrior': '7-day streak',
        'ach.bus_network': 'Bus network king',
        'ach.cargo_master': 'Logistics master',
        'ach.golden_keeper': 'Golden keeper',
        'ach.rescue_hero': 'Rescue hero',
        'ach.stage_clearer': 'Stage clearer',
        'stage.stage_01_first_flow.name': 'Stage 1 · First flow',
        'stage.stage_01_first_flow.desc': 'Get 5 vehicles to their destinations on an L-shaped road.',
        'stage.stage_02_junction.name': 'Stage 2 · Build a junction',
        'stage.stage_02_junction.desc': 'Expand the crossroads and place 1 bus stop.',
        'stage.stage_03_cargo_line.name': 'Stage 3 · Cargo line',
        'stage.stage_03_cargo_line.desc': 'Classify truck cargo and keep golden hour.',
        'stage.stage_04_rescue.name': 'Stage 4 · Rescue ops',
        'stage.stage_04_rescue.desc': 'Clear accidents in a busy city and run bus stops.',
        'goal.trips_completed': 'Complete {n} trips',
        'goal.roads_built': 'Add {n} roads',
        'goal.bus_stops_built': '{n} bus stop(s)',
        'goal.cargo_classified': 'Classify {n} cargo loads',
        'goal.golden_flow_seconds': 'Golden flow {n}s',
        'goal.accidents_cleared': 'Clear {n} accidents',
        'plan.price_usd': '${usd}/mo',
        'plan.price_krw': '₩{krw}',
        'plan.pro.b0': 'No ads',
        'plan.pro.b1': '5 city save slots',
        'plan.pro.b2': 'VIP events · CSV export',
        'plan.pro.b3': '2× daily coins · 1.25× XP',
        'plan.pro_plus.b0': 'Everything in PRO',
        'plan.pro_plus.b1': '10 city save slots',
        'plan.pro_plus.b2': '1.5× XP',
        'plan.ultra.b0': 'Everything in PRO+',
        'plan.ultra.b1': '20 city save slots',
        'plan.ultra.b2': '3× daily coins · 2× XP',
        'canvas.golden': 'Golden hour {s}s · avg {avg}',
        'canvas.hud': 'Zoom {zoom}% · wheel zoom · right-click / inspect-mode drag to pan',
    },
};

const interpolate = (text, vars) => {
    if (!vars) return text;
    return String(text).replace(/\{(\w+)\}/g, (_, key) => (
        vars[key] != null ? String(vars[key]) : `{${key}}`
    ));
};

const readStoredLang = () => {
    try {
        const stored = localStorage.getItem(CITYFLOW_LANG_COOKIE);
        if (stored === 'en' || stored === 'ko') return stored;
    } catch {
        /* ignore */
    }
    const match = document.cookie.match(/(?:^|; )cityflow_lang=(en|ko)/);
    if (match) return match[1];
    const nav = String(navigator.language || navigator.userLanguage || '').toLowerCase();
    return nav.startsWith('ko') ? 'ko' : 'en';
};

let currentLang = readStoredLang();

const writeLangCookie = (lang) => {
    document.cookie = `${CITYFLOW_LANG_COOKIE}=${lang};path=/;max-age=31536000;SameSite=Lax`;
    try {
        localStorage.setItem(CITYFLOW_LANG_COOKIE, lang);
    } catch {
        /* ignore */
    }
};

const t = (key, vars, fallback) => {
    if (typeof vars === 'string' && fallback === undefined) {
        fallback = vars;
        vars = undefined;
    }
    const table = I18N[currentLang] || I18N.en;
    const text = table[key] ?? I18N.ko[key] ?? I18N.en[key] ?? fallback ?? key;
    return interpolate(text, vars);
};

const applyI18n = (root = document) => {
    root.querySelectorAll('[data-i18n]').forEach((el) => {
        el.textContent = t(el.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-html]').forEach((el) => {
        el.innerHTML = t(el.dataset.i18nHtml);
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
        el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder));
    });
    root.querySelectorAll('[data-i18n-title]').forEach((el) => {
        el.setAttribute('title', t(el.dataset.i18nTitle));
    });
    const titled = document.querySelector('title[data-i18n]');
    if (titled) document.title = t(titled.dataset.i18n);
    document.documentElement.lang = currentLang;
};

const updateLangToggle = () => {
    document.querySelectorAll('[data-lang-toggle]').forEach((btn) => {
        btn.textContent = currentLang === 'en' ? t('nav.lang_to_ko') : t('nav.lang_to_en');
        btn.setAttribute('aria-label', currentLang === 'en' ? 'Switch to Korean' : 'Switch to English');
    });
};

const refreshDynamicI18n = () => {
    if (window.uiController) window.uiController.catalogRendered = false;
    if (window.uiBridge?._mergedState) {
        window.uiBridge.applySimulationState(window.uiBridge._mergedState);
    }
    const panel = window.engagementPanel;
    if (panel?.player) {
        panel._stagesLoaded = false;
        panel._leaderboardLoaded = false;
        panel.applyPlayer(panel.player);
        panel.renderStages(panel.player);
        if (document.getElementById('shopModal')?.classList.contains('open')) {
            panel.renderShop(panel.player);
        }
        if (document.getElementById('proModal')?.classList.contains('open')) {
            panel.renderPlans(panel.player);
        }
    }
};

const setLang = (lang) => {
    const next = lang === 'en' ? 'en' : 'ko';
    currentLang = next;
    writeLangCookie(next);
    applyI18n();
    updateLangToggle();
    refreshDynamicI18n();
    window.dispatchEvent(new CustomEvent('cityflow:lang', { detail: { lang: next } }));
};

const bindLangToggle = () => {
    document.querySelectorAll('[data-lang-toggle]').forEach((btn) => {
        if (btn.dataset.langBound === '1') return;
        btn.dataset.langBound = '1';
        btn.addEventListener('click', () => {
            setLang(currentLang === 'en' ? 'ko' : 'en');
        });
    });
    updateLangToggle();
};

const initI18n = () => {
    writeLangCookie(currentLang);
    applyI18n();
    bindLangToggle();
};

window.t = t;
window.i18n = {
    t,
    getLang: () => currentLang,
    setLang,
    applyI18n,
    init: initI18n,
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initI18n);
} else {
    initI18n();
}
