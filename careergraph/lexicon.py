"""Hand-written dictionaries and phrase rules. This file is the extraction logic:
no NER model, parser or library decides what an entity or a relation is.
Everything is matched case-insensitively. {SERVICE}, {PRODUCT} and {ANYCO} get
replaced with the alias lists below (see extract.fill)."""

# canonical name -> (tier, alias patterns)
COMPANIES = {
    # service: the WITCH group, other IT services firms, Big 4 delivery centres
    "TCS": ("service", [r"tcs", r"tata consultancy(?: services)?"]),
    "Infosys": ("service", [r"infosys", r"infy"]),
    "Wipro": ("service", [r"wipro"]),
    "Cognizant": ("service", [r"cognizant", r"cts"]),
    "HCLTech": ("service", [r"hcl(?:tech| technologies)?"]),
    "Accenture": ("service", [r"accenture"]),
    "Capgemini": ("service", [r"capgemini", r"cap gemini", r"capg"]),
    "Tech Mahindra": ("service", [r"tech ?mahindra", r"techm"]),
    "LTIMindtree": ("service", [r"ltimindtree", r"lti", r"mindtree", r"l&t infotech", r"lnt infotech"]),
    "Mphasis": ("service", [r"mphasis"]),
    "Hexaware": ("service", [r"hexaware"]),
    "Persistent": ("service", [r"persistent systems"]),
    "Zensar": ("service", [r"zensar"]),
    "Virtusa": ("service", [r"virtusa"]),
    "Coforge": ("service", [r"coforge"]),
    "Birlasoft": ("service", [r"birlasoft"]),
    "NTT Data": ("service", [r"ntt data"]),
    "DXC": ("service", [r"dxc"]),
    "IBM": ("service", [r"ibm"]),
    "Deloitte": ("service", [r"deloitte"]),
    "KPMG": ("service", [r"kpmg"]),
    "PwC": ("service", [r"pwc"]),
    "EY": ("service", [r"ey gds", r"ernst (?:&|and) young"]),
    "Genpact": ("service", [r"genpact"]),
    "UST": ("service", [r"ust global"]),
    "Sopra Steria": ("service", [r"sopra steria"]),
    # product companies, including product-side captives of banks and retailers
    "Google": ("product", [r"google(?! (?:it|search|meet|drive|forms?|docs?|sheets?|colab|cloud))"]),
    "Microsoft": ("product", [r"microsoft", r"msft"]),
    "Amazon": ("product", [r"amazon"]),
    "Meta": ("product", [r"facebook"]),
    "Flipkart": ("product", [r"flipkart"]),
    "Walmart": ("product", [r"walmart(?: global tech)?"]),
    "Uber": ("product", [r"uber"]),
    "Swiggy": ("product", [r"swiggy"]),
    "Zomato": ("product", [r"zomato"]),
    "Paytm": ("product", [r"paytm"]),
    "PhonePe": ("product", [r"phone ?pe"]),
    "Razorpay": ("product", [r"razorpay"]),
    "Zerodha": ("product", [r"zerodha"]),
    "Groww": ("product", [r"groww"]),
    "Meesho": ("product", [r"meesho"]),
    "Myntra": ("product", [r"myntra"]),
    "Atlassian": ("product", [r"atlassian"]),
    "Adobe": ("product", [r"adobe"]),
    "Salesforce": ("product", [r"salesforce"]),
    "Oracle": ("product", [r"oracle"]),
    "SAP Labs": ("product", [r"sap labs"]),
    "Intuit": ("product", [r"intuit"]),
    "Cisco": ("product", [r"cisco"]),
    "VMware": ("product", [r"vmware"]),
    "Nvidia": ("product", [r"nvidia"]),
    "Qualcomm": ("product", [r"qualcomm"]),
    "Intel": ("product", [r"intel"]),
    "Samsung R&D": ("product", [r"samsung(?: r&d| research| semiconductor)?"]),
    "Freshworks": ("product", [r"freshworks"]),
    "Zoho": ("product", [r"zoho"]),
    "BrowserStack": ("product", [r"browserstack"]),
    "Juspay": ("product", [r"juspay"]),
    "Dream11": ("product", [r"dream ?11"]),
    "Nykaa": ("product", [r"nykaa"]),
    "Zepto": ("product", [r"zepto"]),
    "Goldman Sachs": ("product", [r"goldman(?: sachs)?"]),
    "JPMorgan": ("product", [r"jp ?morgan(?: chase)?", r"jpmc"]),
    "Morgan Stanley": ("product", [r"morgan stanley"]),
    "American Express": ("product", [r"american express", r"amex"]),
    "PayPal": ("product", [r"paypal"]),
    "DE Shaw": ("product", [r"de ?shaw"]),
    "Arcesium": ("product", [r"arcesium"]),
}

# phrases that name a company type without naming a company
GENERIC_TIERS = [
    ("service", r"service[- ]?based|services? (?:company|companies|firm|firms|org|mnc|job|side)|mass recruiters?|it services|witch(?: companies| company)?|sbcs?"),
    ("product", r"product[- ]?based|product (?:company|companies|firm|org|mnc|startup|offer|role|job|side)|faang|maang|big tech|pbcs?"),
    ("startup", r"start[- ]?ups?|early[- ]stage|series [a-d]|seed[- ]stage"),
]

CITIES = {
    "Bengaluru": [r"bangalore", r"bengaluru", r"blr"],
    "Hyderabad": [r"hyderabad", r"hyd"],
    "Pune": [r"pune"],
    "Chennai": [r"chennai"],
    "Mumbai": [r"mumbai", r"bombay"],
    "Delhi NCR": [r"delhi", r"ncr", r"noida", r"gurgaon", r"gurugram"],
    "Kolkata": [r"kolkata", r"calcutta"],
    "Ahmedabad": [r"ahmedabad"],
    "Kochi": [r"kochi", r"cochin"],
    "Coimbatore": [r"coimbatore"],
    "Chandigarh": [r"chandigarh", r"mohali"],
    "Thiruvananthapuram": [r"trivandrum", r"thiruvananthapuram"],
    "Indore": [r"indore"],
    "Jaipur": [r"jaipur"],
}

# ---------- advice ----------
ADVICE_MARKERS = [
    r"\byou (?:should|must|need to|have to|can|could|might want to|would be better)\b",
    r"\b(?:i'?d|i would) (?:suggest|recommend|say|advise|go with|go for|take|join|choose|pick|wait|switch|stay)\b",
    r"\bif i were you\b",
    r"\bin your (?:place|shoes|position|case)\b",
    r"\bmy (?:advice|suggestion|2 cents|two cents|take)\b",
    r"\b(?:suggest|recommend)\b",
    r"\bbetter (?:to|if you|option)\b",
    r"\bno point (?:in )?",
    r"\bit'?s (?:better|wiser|safer|smarter) to\b",
    r"\b(?:imo|imho|in my opinion)\b",
    r"\bgo (?:for|with) (?:it|the|this|that)\b",
]
IMPERATIVE_START = (
    r"^(?:just |definitely |please |simply |better |first |then |so )?"
    r"(?:join|take|accept|switch|wait|negotiate|decline|reject|stay|leave|quit|resign|focus|prepare|learn|start|keep|apply"
    r"|grind|go|ask|move|grab|choose|pick|skip|avoid|don'?t|do not|never|try|get|build|practice|upskill|consider|hold|jump|run|look|ignore|explore)\b"
)

# (pattern, option). Flipped to "opposes" when a negation sits right before the match.
OPTION_CUES = [
    (r"\b(?:join(?:ing)?|accept(?:ing)?|tak(?:e|ing)|go(?:ing)? with|grab(?:bing)?)\b[^.!?,;]{0,30}?\b(?:{SERVICE})\b", "accept_service"),
    (r"\bstay(?:ing)? (?:at|in|with) (?:{SERVICE})\b", "accept_service"),
    (r"\bwait(?:ing)? (?:for|till|until)\b[^.!?,;]{0,25}?\b(?:product|better|good|bigger)\b", "wait_for_product"),
    (r"\b(?:decline|declining|reject(?:ing)?|skip(?:ping)?|pass on|say no to)\b[^.!?,;]{0,25}?\b(?:{SERVICE}|the offer|this offer|that offer)\b", "wait_for_product"),
    (r"\bkeep (?:preparing|grinding|applying|trying) for product\b", "wait_for_product"),
    (r"\bhold out\b", "wait_for_product"),
    (r"\bswitch(?:ing)? (?:now|asap|immediately|right away|right now|as soon as possible)\b", "switch_now"),
    (r"\b(?:join(?:ing)?|accept(?:ing)?|tak(?:e|ing)|go(?:ing)? for|go(?:ing)? with|grab(?:bing)?)\b[^.!?,;]{0,30}?\b(?:{PRODUCT})\b", "switch_now"),
    (r"\b(?:leav(?:e|ing)|quit(?:ting)?|get out of|run from|escape|exit)\b[^.!?,;]{0,20}?\b(?:{SERVICE})\b", "switch_now"),
    (r"\bjump ship\b", "switch_now"),
    (r"\b(?:quit(?:ting)?|resign(?:ing)?|leav(?:e|ing))\b[^.!?,;]{0,25}?\bwithout\s+(?:an?\s+|any\s+)?(?:offer|job)\b", "resign_without_offer"),
    (r"\b(?:quit(?:ting)?|resign(?:ing)?)\b[^.!?,;]{0,25}?\b(?:and|to)\s+(?:then\s+)?(?:prepare|prep|focus|study|grind|upskill|learn|practi[cs]e)\b", "resign_without_offer"),
    (r"\bleav(?:e|ing)\s+(?:your|the|my|ur)\s+(?:current\s+)?job\b[^.!?,;]{0,25}?\b(?:and|to)\s+(?:then\s+)?(?:prepare|prep|focus|study|grind|upskill|learn|practi[cs]e)\b", "resign_without_offer"),
    (r"\b(?:take|taking)\s+(?:a\s+)?(?:short\s+|small\s+|career\s+|long\s+)?(?:break|gap)\b", "resign_without_offer"),
    (r"\b(?:upskill(?:ing)?|prepar(?:e|ing)|grind(?:ing)?|practi[cs](?:e|ing)|learn(?:ing)?|study(?:ing)?|focus on|work on)\b[^.!?]{0,60}?\b(?:then|and then|before|after that|later)\b[^.!?,;]{0,20}?\b(?:switch|move|jump|apply)", "upskill_then_switch"),
    (r"\bswitch (?:after|later|in) (?:\d+(?:\.\d+)?|a|one|two|a couple of|few|some)\s*(?:years?|yrs?|months?)\b", "upskill_then_switch"),
    (r"\b(?:complete|finish|get|gain|do|spend) (?:at ?least |minimum )?(?:1|one|a|2|two|1\.5) (?:year|yr)s?\b[^.!?]{0,40}?\b(?:switch|move|leave|jump)\b", "upskill_then_switch"),
    (r"\bgain (?:some )?experience (?:and|then) switch\b", "upskill_then_switch"),
    (r"\b(?:you (?:should|must|can|could|need to|have to)|try to|always|just|definitely|better to|i'?d|i would|make sure to)\s+(?:also\s+|always\s+|still\s+)?negotiate\b", "negotiate"),
    (r"^\W*(?:just |also |definitely |please |so |and |but |first )?negotiate\b", "negotiate"),
    (r"\bcounter[- ]?offer\b", "negotiate"),
    (r"\bask (?:them |hr )?for (?:more|a (?:higher|better)|\d+)", "negotiate"),
    (r"\buse (?:it|this|that|the offer) (?:as|for) (?:leverage|negotiation)\b", "negotiate"),
    (r"\bkeep (?:interviewing|applying|looking|giving interviews|searching|hunting)\b", "accept_and_keep_interviewing"),
    (r"\b(?:continue|keep) (?:your |the )?(?:job )?(?:hunt|search)\b", "accept_and_keep_interviewing"),
    (r"\bwhile (?:working|you work|being employed)\b", "accept_and_keep_interviewing"),
]
# (pattern, option, stance): phrases that already carry their meaning, so no negation check
FIXED_CUES = [
    (r"\bdon'?t (?:wait|sit idle|sit at home|stay unemployed|be jobless|stay jobless)\b(?![^.!?]{0,25}\bswitch)", "accept_service", 1),
    (r"\b(?:don'?t|never|do not)\b[^.!?,;]{0,15}?\b(?:join(?:ing)?|accept(?:ing)?|take|go to)\b[^.!?,;]{0,20}?\b(?:{SERVICE})\b", "accept_service", -1),
    # quitting with nothing lined up is its own option; leaving FOR something is the product move
    (r"\b(?:don'?t|never|do not|shouldn'?t|should not)\s+(?:just\s+|ever\s+|blindly\s+)?(?:quit|resign)\b(?![^.!?,;]{0,30}?\b(?:for|to join)\s+(?:an?\s+|the\s+)?(?:{PRODUCT}|startup|product|offer|new|another))", "resign_without_offer", -1),
    (r"\b(?:don'?t|never|do not)\s+(?:just\s+)?leave\s+(?:your|the|this|ur)\s+(?:current\s+)?job\b(?![^.!?,;]{0,30}?\b(?:for|to join)\b)", "resign_without_offer", -1),
    (r"\b(?:don'?t|never|do not)\s+(?:just\s+)?leave\b[^.!?,;]{0,30}?\b(?:for|to join)\s+(?:an?\s+|the\s+)?(?:{PRODUCT}|startup|product|offer|new|another)", "switch_now", -1),
    (r"\b(?:don'?t|never|do not)\s+(?:just\s+)?(?:switch|jump)\b", "switch_now", -1),
    (r"\b(?:don'?t|do not) (?:wait|delay)\b[^.!?,;]{0,20}?\bswitch", "switch_now", 1),
    (r"\bsomething is better than nothing\b", "accept_service", 1),
    (r"\bbird in (?:the )?hand\b", "accept_service", 1),
    (r"\b(?:job|offer) in hand is better\b", "accept_service", 1),
]
# "take the offer" means a different option depending on the thread's situation
GENERIC_ACCEPT = r"\b(?:take|accept|join|go for|go with|grab)\s+(?:the|this|that|it|this one|that one)\b(?!\s+(?:with|easy|seriously|lightly|personally))"
NEGATION_BEFORE = r"(?:\bdon'?t|\bdo not|\bnever|\bavoid|\bno need to|\bnot worth|\bshouldn'?t|\bwouldn'?t|\bwon'?t|\bstop|\bno point(?: in)?|\bnot)\s+(?:\w+\s+)?$"

# ---------- outcomes ----------
OUTCOME_DECISION = (
    r"\b(?:i|we)\s+(?:also\s+|then\s+|had\s+|have\s+|finally\s+|eventually\s+|later\s+|just\s+|too\s+)?"
    r"(?:switched|joined(?!\s+(?:the\s+|a\s+|my\s+)?(?:college|school|course|class|bootcamp|university|uni|reddit|this sub)\b)"
    r"|moved(?!\s+(?:back\s+)?(?:home|to\s+(?:my\s+)?hometown)\b)"
    r"|left(?!\s+(?:the\s+|my\s+)?(?:college|school|campus|university|uni|home|hostel|india|the country)\b)"
    r"|quit|resigned|absconded|took|accepted|declined|rejected|stayed|waited|negotiated|cracked|landed"
    r"|jumped|got placed|got a job|turned down|did not join|didn'?t join|started (?:at|in|with|working)|started my career (?:at|in|with))\b"
)
OUTCOME_RESULT = [
    r"\bnow\b", r"\btoday\b", r"\bcurrently\b",
    r"\b(?:after|within|in) (?:\d+(?:\.\d+)?|a|one|two|three|few|couple of) (?:years?|months?|yrs?)\b",
    r"\b\d+ (?:years?|months?|yrs?) (?:later|ago)\b", r"\blooking back\b", r"\bin hindsight\b",
    r"\bbest decision\b", r"\bworst decision\b", r"\bregret", r"\bhike\b", r"\b(?:doubled|tripled)\b",
    r"\blaid off\b", r"\blayoffs?\b", r"\bglad\b", r"\bhapp(?:y|ier)\b", r"\bworth it\b", r"\bmistake\b",
    r"\bbench\b", r"\blearn(?:ed|t) a lot\b", r"\bstill\b", r"\b(?:two|three|four|five|\d+) times (?:more|the|my|what)\b",
]
# what the person chose, checked in this order on their first-person decision sentences
CHOICE_RULES = [
    # quit with nothing lined up (checked first: "I quit to prepare and cracked Amazon" is still quitting first)
    (r"\b(?:quit|resigned|left)\b[^.!?|]{0,60}?\bwithout\s+(?:\w+\s+){0,3}(?:offer|job)\b", "resign_without_offer"),
    (r"\b(?:quit|resigned|left)\b[^.!?|]{0,40}?\b(?:to|and)\s+(?:then\s+)?(?:prepare|prep|focus|study|upskill|learn|grind|practi[cs]e)", "resign_without_offer"),
    (r"\b(?:quit|resigned|left)\b[^.!?]{0,120}?\b(?:jobless|unemployed|no job|career gap|gap year|sitting at home|sat at home)\b", "resign_without_offer"),
    (r"\b(?:i|we)\s+(?:took|had taken)\s+(?:a\s+)?(?:\d+\s*(?:months?|years?)\s+|short\s+|long\s+|career\s+)?(?:break|gap)\b", "resign_without_offer"),
    (r"\b(?:prepar\w*|grind\w*|practi[cs]\w*|upskill\w*|learn\w*|stud(?:y|ied)|leetcode|dsa)\b[^.!?]{0,80}?\b(?:switched|moved|got (?:a |an |the )?(?:job|offer)|got into|cracked|landed|joined|jumped)\b", "upskill_then_switch"),
    (r"\b(?:switched|moved|got (?:a |an |the )?(?:job|offer)|got into|cracked|landed|jumped|left)\b[^.!?]{0,60}?\bafter\b[^.!?]{0,40}?(?:prepar|grind|practi|upskill|learn|stud|\d+(?:\.\d+)?\s*(?:years?|yrs?|months?)|(?:a|one|two|three) (?:years?|yrs?))", "upskill_then_switch"),
    (r"\b(?:joined|stayed|started|worked)\b[^.!?]{0,60}?\b(?:{SERVICE})\b[^.!?]{0,80}?\b(?:switched|moved|jumped|left)\b", "upskill_then_switch"),
    (r"\b(?:i|we) (?:also |then |successfully )?(?:negotiated|countered|got a counter[- ]?offer)", "negotiate"),
    # "I left a job offer for Sopra Steria" = picked the service company
    (r"\b(?:left|declined|rejected|turned down|gave up)\s+(?:an?\s+|the\s+|my\s+|another\s+|other\s+)?(?:job\s+)?offers?\s+(?:for|to join)\s+(?:{SERVICE})", "accept_service"),
    # turning down a product offer = staying where you are
    (r"\b(?:declined|rejected|turned down|said no to|didn'?t join|did not join|gave up)\b(?:(?!\band\b|\bbut\b)[^.!?,;]){0,30}?\b(?:{PRODUCT})\b", "accept_service"),
    (r"\b(?:declined|rejected|turned down|said no to|didn'?t join|did not join)\b(?:(?!\band\b|\bbut\b)[^.!?,;]){0,30}?\b(?:{SERVICE})\b", "wait_for_product"),
    (r"\b(?:declined|rejected|turned down|said no to)\s+(?:the|that|this|an?|my)\s+(?:\w+\s+)?offer\b", "GENERIC_DECLINE"),
    (r"\bwaited\b", "wait_for_product"),
    (r"\b(?:joined|accepted|took|stayed|started)\b[^.!?,;]{0,40}?\b(?:{SERVICE})\b", "accept_service"),
    # leaving only counts as the product move when the story says where they went
    (r"\b(?:left|quit|resigned|absconded)\b[^.!?]{0,100}?\b(?:{PRODUCT}|product|startup|pbc|gcc)\b", "switch_now"),
    # "switched" only counts when it is about a job or company, not "switched to the Odin Project"
    (r"\b(?:switched|moved|jumped|made (?:a|the|my) switch)\b[^.!?|]{0,60}?\b(?:to|into)\s+(?:an?\s+|the\s+|my\s+)?(?:{PRODUCT}|product|startup|mnc|gcc|pbc)\b", "switch_now"),
    (r"\b(?:joined|accepted|took|got placed|cracked|landed|got a job|started)\b[^.!?,;]{0,40}?\b(?:{PRODUCT})\b", "switch_now"),
    (r"\b(?:took|accepted|joined)\s+(?:the|that|this|an?)\s+(?:\w+\s+)?offer\b", "GENERIC"),
    (r"\bstayed\b", "accept_service"),
]
NEGATED_POSITIVE = [
    r"\bnot (?:very |really |that |so )?(?:happy|glad|good|great|worth it)\b",
    r"\b(?:wasn'?t|isn'?t|was not|is not) worth\b",
]
POSITIVE_OUTCOME = [
    r"\bno regrets?\b", r"\bdon'?t regret\b", r"\b(?:won'?t|will not|wouldn'?t|never) regret(?:ted)?\b", r"\bnot a mistake\b",
    r"\bnever looked back\b", r"\b(?:don'?t|do not|never) (?:intend|plan|want) to (?:go back|return)\b", r"\bnever going back\b",
    r"\bbest (?:decision|thing|move|choice)\b", r"\bgood (?:decision|move|choice|call)\b", r"\bworth it\b", r"\bpaid off\b",
    r"\b(?:really |very |so |much )?(?:happy|happier|glad)\b", r"\blearn(?:ed|t) a lot\b", r"\bgreat (?:learning|experience|decision|move)\b",
    r"\b(?:amazing|awesome)\b", r"\b(?:doubled|tripled)\b", r"\b\d+(?:\.\d+)?\s*x\b", r"\b\d{2,3}\s*% hike\b", r"\b(?:good|huge|great|solid) hike\b",
    r"\bmuch better\b", r"\blove (?:it|my job|the work)\b", r"\bgrew a lot\b",
    r"\bgood (?:dev |development )?(?:project|team|work|manager|culture|growth)\b", r"\bpaid (?:much |a lot |way )?more\b",
    r"\b(?:two|three|four|five|\d+) times (?:more|the salary|my salary)\b", r"\bbetter (?:pay|salary|package|work|growth|team|culture)\b",
]
NEGATIVE_OUTCOME = [
    r"\bregret(?:ted|s)?\b", r"\bworst (?:decision|mistake|move|thing)\b", r"\bbad (?:decision|move|choice|call)\b", r"\bmistake\b",
    r"\blaid off\b", r"\blayoffs?\b", r"\bfired\b", r"\bterminated\b", r"\bkicked\b", r"\btoxic\b", r"\bburn(?:ed|t)? ?out\b", r"\bstuck\b",
    r"\bon (?:the )?bench\b", r"\bno growth\b", r"\bno learning\b", r"\bwasted\b", r"\bshould(?: not|n'?t)? have\b",
    r"\bstruggl(?:ed|ing)\b", r"\bunderpaid\b", r"\bterrible\b", r"\bmiserable\b", r"\bshit(?:ty)?\b", r"\bsucks?\b", r"\bpathetic\b",
    r"\bjobless\b", r"\bunemployed\b", r"\b(?:don'?t|do not) have (?:a|any) job\b", r"\bfrustrat(?:ed|ing)\b", r"\brescind(?:ed)?\b",
    r"\bno work\b", r"\bnot (?:yet )?onboarded\b", r"\bstill waiting\b",
    r"\brevoked\b", r"\bwaiting for (?:the |my )?(?:onboarding|joining|offer letter)\b",
]

# ---------- factors ----------
FACTOR_CUES = {
    "pay": [r"\bsalary\b", r"\bctc\b", r"\blpa\b", r"\bhikes?\b", r"\bpay(?:s|ing)?\b", r"\bpackage\b", r"\bmoney\b", r"\bcompensation\b", r"\bin[- ]?hand\b"],
    "learning": [r"\blearn(?:ing|t|ed)?\b", r"\btech stack\b", r"\bskills?\b", r"\bexposure\b", r"\blegacy\b", r"\bsupport (?:project|role|work)\b", r"\bmaintenance\b", r"\bquality of work\b"],
    "job_security": [r"\bjob security\b", r"\bsecure\b", r"\bstab(?:le|ility)\b", r"\blay ?offs?\b", r"\blaid off\b", r"\bfired\b"],
    "wlb": [r"\bwork[- ]?life\b", r"\bwlb\b", r"\blong hours\b", r"\bovertime\b", r"\bweekends?\b", r"\bburn(?:ed|t)? ?out\b", r"\bstress(?:ful)?\b", r"\btoxic\b", r"\bpressure\b"],
    "notice_period": [r"\bnotice period\b", r"\b(?:30|60|90) days? notice\b", r"\bbuy ?out\b", r"\bearly release\b", r"\bserving notice\b"],
    "bond": [r"\bbond\b", r"\bservice agreement\b", r"\btraining (?:bond|agreement)\b"],
    "bench": [r"\bbench\b", r"\bunallocated\b", r"\bno project\b", r"\bproject allocation\b"],
    "brand_value": [r"\bbrand\b", r"\bresume value\b", r"\bname on (?:the |your )?(?:resume|cv)\b", r"\bfaang\b", r"\bmaang\b", r"\bbig tech\b"],
}

# ---------- replies and lived experience ----------
DISAGREE_MARKERS = [
    r"\b(?:i )?(?:strongly |hard |totally )?disagree\b", r"\bnot true\b", r"\b(?:bad|terrible|horrible|worst|wrong) advice\b",
    r"\bthat'?s (?:not true|wrong|bs|bullshit)\b", r"^(?:no|nope|nah)\b[,.! ]", r"\bnot necessarily\b", r"\bdon'?t listen to\b",
]
AGREE_MARKERS = [
    r"^(?:this|exactly|true|agreed?|\+1|100%|correct|well said|seconded|absolutely|so true)\b", r"\bi agree\b",
    r"\b(?:good|solid|best|great) advice\b",
]
EXPERIENCE_MARKERS = [
    r"\bin my experience\b", r"\bi(?:'ve| have) (?:worked|been working|been) (?:at|in|with|for)\b", r"\bi work(?:ed)? (?:at|in|for|with)\b",
    r"\bmy (?:current |previous |last )?(?:company|employer|org|team|manager)\b", r"\bi(?:'ve| have) seen\b",
    r"\b(?:\d+|ten|five) ?\+? ?(?:yoe|years) (?:in|of) (?:the )?industry\b", r"\bi was (?:in|at) (?:the )?same\b",
]

# ---------- added after testing on real comments ----------
# a sentence only counts as advice when it is phrased as advice (imperative, "you should", "better to")
DIRECTIVE_MARKERS = [
    r"\byou\b[^.!?]{0,25}\b(?:should|must|can|could|need|have to|will|would|might)\b",
    r"\b(?:better to|it'?s better|go for|go with)\b",
]
# "Had I stayed...", "If I joined..." and questions are not things that happened
HYPOTHETICAL = r"^\W*(?:if|had i|even if|what if)\b|\bif i\b|\?"
# "because the team was toxic" is the reason for a decision, not how it turned out
REASON_CLAUSE = r"\b(?:because|since|due to|coz|cuz)\b.*?(?=,|;|\band\b|\bbut\b|$)"
# words that mean a job or company move, used by the topic filter ("switch to Python" does not count)
JOB_MOVE = (
    r"\b(?:offers?|offered|offer letter|selected (?:in|at|for|by)|got selected|placed (?:in|at)|got placed"
    r"|join(?:ing)?(?! (?:the |a |this |our )?(?:college|course|class|bootcamp|community|discord|group|server|sub))|accept(?:ing)?"
    r"|quit(?:ting)?|resign(?:ing)?|leav(?:e|ing) (?:my |the |this |a )?(?:job|company|org|{SERVICE})|abscond(?:ing)?"
    r"|switch(?:ing)? (?:to|from|into) (?:an? |the )?(?:{PRODUCT}|{SERVICE}|product|service|startup|mnc|compan(?:y|ies)|jobs?)"
    r"|(?:job|company) switch|switch(?:ing)? (?:jobs?|compan(?:y|ies))"
    r"|(?:transition|move|moving|shift)(?:ing)? (?:to|from|into) (?:an? |the )?(?:{PRODUCT}|{SERVICE}|product|service|startup|mnc)"
    r"|vs\.?|versus|which (?:one|is better|company|offer|to (?:choose|pick|join))|choos(?:e|ing)|decide|decision|dilemma|confused)\b"
)
# company-type words: a strong topic signal in a title, but in a body sentence they only name the company type
TIER_WORDS = r"\b(?:product[- ]based|service[- ]based|pbcs?|sbcs?|witch|mass recruiters?)\b"
# a comment that advises about one option and then says "I did it" is an outcome for that option
DID_IT = r"\b(?:i|we)(?:'?ve| have)?\s+(?:also\s+|too\s+)?(?:did|done|tried)\s+(?:it|that|this|the same|exactly that)\b"
# sentences about the reader or someone else are not part of the writer's own story
OTHER_PERSON = r"\b(?:you|your|u|he|she|his|her|friends?|brother|sister|cousin|colleagues?|neighbou?rs?|seniors?|batchmates?)\b"
# a later move to a product company after joining a service one ("now I'm at a PBC")
LATER_MOVE = (r"\b(?:switched\s+(?:to|jobs?|compan(?:y|ies)|over)|made (?:a|the|my) (?:first )?switch)\b"
              r"|\b(?:moved|jumped|got placed|got (?:an? )?(?:offer|job)|joined|landed|cracked|now|currently|today)\b[^.!?|]{0,40}?"
              r"\b(?:at|in|with|for|to|into)\s+(?:an?\s+|another\s+|the\s+)?(?:{PRODUCT}|product|pbc|startup|gcc)\b")
# pay growth only counts when the later amount is what the writer earns, not an offer or someone else's pay
GROWTH_CUE = r"\b(?:now|currently|today|presently|at present|reached|making|earning|drawing|getting|sitting (?:on|at)|pull(?:ed)?(?: it)? up to|hike to|went (?:up )?to|switched|moved|joined|landed|cracked|got)\b"
NOT_GROWTH = r"\b(?:offer(?:ed|s)?|expect(?:ed|ing|ation)?|ask(?:ed|ing)?|target|want(?:ed)?|aim(?:ing)?|hoping|friends?|he|she|his|her)\b"
# what other people said is not how it went ("my team said I was making a mistake")
REPORTED_SPEECH = r"\b(?:said|says|told(?: me)?|were like|was like|warned(?: me)?)\b.*$"
# "...and the people around me who joined WITCH are on bench" is about others, so the writer's story stops there
OTHERS_CLAUSE = (r"\b(?:(?:the\s+)?(?:people|guys|folks|others|everyone|batchmates|colleagues)\s+(?:around me\s+|i know\s+)?(?:who|that)"
                 r"|my\s+(?:friends?|brother|sister|cousin|colleagues?|seniors?|batchmates?|roommate|neighbou?rs?))\b.*$")
# "I wasn't on bench" is not a bad outcome
NEGATED_NEGATIVE = [r"\b(?:not|never|wasn'?t|weren'?t|isn'?t|aren'?t|didn'?t|haven'?t|hasn'?t|no longer)\s+(?:\w+\s+)?"
                    r"(?:on (?:the )?bench|stuck|laid off|fired|toxic|regret(?:ted)?|struggl(?:ed|ing)|underpaid)\b"]
