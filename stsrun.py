# 2025-08-22 by SteveWithaB
# Below is mostly terrible code for importing run files from Baalor's run history into a MySQL database
# Runs used were from the primary BaalorA20 profile and is only set for base game material
# Some refactoring/optimizing can be done but this first pass is to prove it can work
# This is dependent on connecting to a MySQL database with defined tables. Obviously can be changed to any DB type
# I've added comments below where I think they were needed

import json
import mysql.connector
from os import listdir

# Main function for inserting data
# values should be a list of tuples containing column data in order of columns in the target table
# values could have a differnt order if stmt explicitly gives the order the values are in
def InsertData(stmt,values):
    cnx = mysql.connector.connect(user='username', password='password', host='127.0.0.1', database='sts')
    cursor=cnx.cursor()
    cursor.executemany(stmt,values)
    cnx.commit()
    cnx.close()

# Due to shop purchase information not containing an object type, this is needed to run one update statement to set those
# Can handle any update statement, however.
def UpdateData(stmt):
    cnx = mysql.connector.connect(user='username', password='password', host='127.0.0.1', database='sts')
    cursor=cnx.cursor()
    cursor.execute(stmt)
    cnx.commit()
    cnx.close()

# Code stolen from Faely who translated it from C
# Needed as the seed stored is not what's shown in-game, so it's converted here
def ConvertSeed(seed_played):
    c = "0123456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
    s = []
    seed_played_ingame = ""
    seed_bytes = int(seed_played).to_bytes(20, "big", signed=True).lstrip(b"\xff")
    seed_from = int.from_bytes(seed_bytes, "big")
    while seed_from:
        seed_from, i = divmod(seed_from, 35)
        seed_played_ingame = c[i] + seed_played_ingame
        s.append(c[i])
    s.reverse()
    return seed_played_ingame

# Loads runinfo table as defined at bottom of this script
def RunInfo(rundata):
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    character_chosen = rundata["character_chosen"]
    playtime = rundata["playtime"]
    floor_reached = rundata["floor_reached"]
    local_time = rundata["local_time"]
    seed_source_timestamp = rundata["seed_source_timestamp"]
    circlet_count = rundata["circlet_count"]
    seed_played = rundata["seed_played"]
    seed_played_ingame = ConvertSeed(rundata["seed_played"])
    is_trial = rundata["is_trial"]
    is_prod = rundata["is_prod"]
    is_daily = rundata["is_daily"]
    chose_seed = rundata["chose_seed"]
    build_version = rundata["build_version"]
    victory = rundata["victory"]
    player_experience = rundata["player_experience"]
    is_beta = rundata["is_beta"]
    is_endless = rundata["is_endless"]
    is_ascension_mode = rundata["is_ascension_mode"]
    ascension_level = rundata["ascension_level"]
    gold = rundata["gold"]
    
    # counters comes from relic_stats key, which may not exist
    try:
        total_combats = rundata["relic_stats"]["counters"][0]
        total_turns = rundata["relic_stats"]["counters"][1]
    except:
        total_combats = 0
        total_turns = 0
    score = rundata["score"]
    
    # Some runs did not have this key. Default to floor 0 if not there
    try:
        green_key = rundata["green_key_taken_log"]
    except:
        green_key = 0
    
    # Victories don't have this
    try:
        killed_by = rundata["killed_by"]
    except:
        killed_by = ""
    stmt = "INSERT INTO runinfo values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    values = [(play_id, timestamp, character_chosen,playtime,floor_reached,local_time,seed_source_timestamp,circlet_count,seed_played,seed_played_ingame,is_trial,is_prod,is_daily,chose_seed,build_version,victory,player_experience,is_beta,is_endless,is_ascension_mode,ascension_level,gold,total_combats,total_turns,score,green_key,killed_by)]
    InsertData(stmt, values)

# Loads masterdecks table as defined at bottom of this script
def MasterDeck(play_id, timestamp, master_deck):
    card_list = []
    for card in master_deck:
        card_list.append((play_id, timestamp, card))
    stmt = "INSERT INTO masterdecks values (%s, %s, %s)"
    InsertData(stmt,card_list)

# Loads floorinfo table as defined at bottom of this script
def FloorInfo(rundata):
    floor_info = []
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    path_per_floor = rundata["path_per_floor"] #Result of clicked node. Does contain boss chest and transition floors
    path_taken = rundata["path_taken"] #Actual node clicked on, therefore does not contain boss chest or transition floors
    path_taken_new = []
    gold_per_floor = rundata["gold_per_floor"]
    current_hp_per_floor = rundata["current_hp_per_floor"]
    max_hp_per_floor = rundata["max_hp_per_floor"]
    if rundata["victory"]: #Gold, current hp, and max hp don't account for the victory screen, but path_per_floor does
        gold_per_floor.append(rundata["gold"])
        current_hp_per_floor.append(current_hp_per_floor[-1])
        max_hp_per_floor.append(max_hp_per_floor[-1])
    floor_exit_playtime = []
    
    #Runs that abandon or lose at neow or floor 1 don't have this
    try:
        floor_exit_playtime = rundata["floor_exit_playtime"]
    except:
        floor_exit_playtime.append(rundata["playtime"])
    else:
        floor_exit_playtime.append(rundata["playtime"])
        
    y=0 #This is used to iterate through path_taken, which doesn't contain boss chest or transition floors
    for x in range(len(path_per_floor)):            
        if path_per_floor[x] == None:
            path_taken_new.append("C") #Adds boss chest and transition floors to path_taken data. C was picked for CHEST and CINEMATIC
            path_per_floor[x] = "C"
        else:
            path_taken_new.append(path_taken[y])
            y+=1
    for z in range(len(path_per_floor)):
        floor_info.append((play_id, timestamp, z+1,path_taken_new[z], path_per_floor[z],gold_per_floor[z],current_hp_per_floor[z],max_hp_per_floor[z],floor_exit_playtime[z]))
    stmt = "INSERT INTO floorinfo values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    InsertData(stmt,floor_info)

# Loads scoredetail table as defined at the bottom of this script
def ScoreDetail(play_id, timestamp, score_breakdown):
    score_detail = []
    
    #Score details are broken into "Score name: Value" so we split on : to separate
    for score in score_breakdown:
        score_detail.append((play_id, timestamp, score.split(": ")[0], score.split(": ")[1]))
    stmt = "INSERT INTO scoredetail values (%s,%s,%s,%s)"
    InsertData(stmt, score_detail)

# Loads cardrewards table as defined at the bottom of this script
# Contains any cards given on a reward type screen, including Library event and Orrery
def CardRewards(play_id, timestamp, card_choices):
    choice_list = []
    for choice in card_choices:
        for skipped in choice["not_picked"]:
            choice_list.append((play_id,timestamp,choice["floor"],"N",skipped))
        if choice["picked"].upper() != "SKIP":
                choice_list.append((play_id,timestamp,choice["floor"],"Y",choice["picked"]))
    choice_list = list(dict.fromkeys(choice_list))
    stmt = "INSERT INTO cardrewards values (%s,%s,%s,%s,%s)"
    InsertData(stmt,choice_list)

# Loads relics table as defined at the bottom of this script
# Uses keys for relic names. relic_stats doesn't have all relics but obtain_stats within relic_stats does
# Obtain stats are in the order of: floor obtained, combats before obtaining the relic, and turns before obtaining the relic
# Turns and combats do include events such as Red Mask Gang and Colosseum.
def Relics(play_id, timestamp, relic_stats):
    relic_list = []
    for relic in relic_stats["obtain_stats"][0].keys():
        try:
            relic_stat = relic_stats[relic]
        except:
            relic_stat = ""
        if type(relic_stat) is list:
            if len(relic_stat) == 1:
                relic_list.append((play_id, timestamp,relic,relic_stats["obtain_stats"][0][relic],relic_stats["obtain_stats"][1][relic],relic_stats["obtain_stats"][2][relic],relic_stat[0]))
            else:
                relic_list.append((play_id, timestamp,relic,relic_stats["obtain_stats"][0][relic],relic_stats["obtain_stats"][1][relic],relic_stats["obtain_stats"][2][relic],str(relic_stat)))
        else:
            relic_list.append((play_id, timestamp,relic,relic_stats["obtain_stats"][0][relic],relic_stats["obtain_stats"][1][relic],relic_stats["obtain_stats"][2][relic],relic_stat))
    stmt = "INSERT INTO relics values (%s,%s,%s,%s,%s,%s,%s)"
    print(relic_list)
    InsertData(stmt, relic_list)

# Loads relicsmissed table as defined at the bottom of this script
# Opted to include Blue Key here, as well as shops seen and not purchased at shops. Includes relics intentionally skipped on rewards
def RelicsMissed(rundata):
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    relics_missed = []
    # Sometimes runs don't have the following keys within the try statements, thus the try statement.
    try:
        shop_contents = rundata["shop_contents"]
        for shop in shop_contents:
            for relic in shop["relics"]:
                relics_missed.append((play_id, timestamp, shop["floor"], relic, "Shop"))
    except:
        pass
    try:
        blue_key = rundata["blue_key_relic_skipped_log"]
    except:
        pass
    else:
        relics_missed.append((play_id, timestamp, blue_key["floor"], blue_key["relicID"], "Blue Key"))
    try:
        rewards_skipped = rundata["rewards_skipped"]
    except:
        pass
    else:
        for skipped in rewards_skipped:
            if len(skipped["relics"]) > 0:
                for relic in skipped["relics"]:
                    relics_missed.append((play_id, timestamp, skipped["floor"], relic, "Skipped"))
    if len(relics_missed) > 0:
        stmt = "INSERT INTO relicsmissed values (%s, %s, %s, %s, %s)"
        InsertData(stmt,relics_missed)

# Loads restsites table as definied at the bottom of this script
# RECALL and REST don't have data key. Dream Catcher choices included in cardrewards data
def RestSites(play_id, timestamp, campfire_choices):
    campfire_list = []
    for campfire in campfire_choices:
        if 'data' not in campfire:
            campfire_list.append((play_id, timestamp, campfire["floor"], campfire["key"],""))
        else:
            campfire_list.append((play_id, timestamp, campfire["floor"], campfire["key"],campfire["data"]))
    stmt = "INSERT INTO restsites values (%s, %s, %s, %s, %s)"
    InsertData(stmt, campfire_list)

# Loads bossrelics table as defined at the bottom of this script
# Decided to have one row per relic with a field indicating if it was picked or skipped.
# Floors hard-coded as those are constant between runs
def BossRelics(play_id,timestamp,boss_relics):
    relic_list = []
    f = 16
    for bossrelic in boss_relics:
        for not_picked in bossrelic["not_picked"]:
            relic_list.append((play_id,timestamp,f,"N",not_picked))
        if 'picked' in bossrelic.keys():
            relic_list.append((play_id,timestamp,f,"Y",bossrelic["picked"]))
        f=33
    stmt = "INSERT INTO bossrelics values (%s,%s,%s,%s,%s)"
    InsertData(stmt,relic_list)

# Loads combats table as defined at the bottom of this script
def Combats(play_id, timestamp, damage_taken):
    combat_list = []
    for combat in damage_taken:
        combat_list.append((play_id, timestamp, combat["floor"], combat["turns"], combat["enemies"],combat["damage"]))
    stmt = "INSERT INTO combats values (%s, %s, %s, %s, %s, %s)"
    InsertData(stmt, combat_list)

# Loads lessonlearned table as defined at the bottom of this script
# Lesson learned data includes all floors, including boss chest and transition floors, so we can use the list index+1 as floor
def LessonLearned(play_id, timestamp, lesson_learned):
    learned_list = []
    for x in range(len(lesson_learned)):
        if len(lesson_learned[x]) > 0:
            for card in lesson_learned[x]:
                learned_list.append((play_id, timestamp, x+1, card))
    if len(learned_list) > 0:
        stmt = "INSERT INTO lessonlearned values (%s, %s, %s, %s)"
        InsertData(stmt,learned_list)

# Loads potiondetail table as defined at the bottom of this script
# Gets potions obtained by rewards, events, entropic brew, and alchemize
# Also loads data for discarded or skipped potions, as well as used potions
def PotionDetails(rundata):
    potion_list = []
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    
    try:
        potions_obtained = rundata["potions_obtained"]
    except:
        pass
    else:
        for obtained in potions_obtained:
            potion_list.append((play_id,timestamp,obtained["floor"],"Obtained",obtained["key"]))
    
    try:
        entropic = rundata["potions_obtained_entropic_brew"]
    except:
        pass
    else:
        for e in range(len(entropic)):
            for potion in entropic[e]:
                potion_list.append((play_id,timestamp,e+1,"Brewed",potion))
    
    try:
        alchemize = rundata["potions_obtained_alchemize"]
    except:
        pass
    else:
        for a in range(len(alchemize)):
            for potion in alchemize[a]:
                potion_list.append((play_id,timestamp,a+1,"Alchemize",potion))
    
    try:
        discard = rundata["potion_discard_per_floor"]
    except:
        pass
    else:
        for d in range(len(discard)):
            for potion in discard[d]:
                potion_list.append((play_id,timestamp,d+1,"Discarded",potion))
    try:
        rewards_skipped = rundata["rewards_skipped"]
    except:
        pass
    else:
        for skipped in rewards_skipped:
            for potion in skipped["potions"]:
                potion_list.append((play_id,timestamp,skipped["floor"],"Skipped",potion))
    try:
        potion_use = rundata["potion_use_per_floor"]
    except:
        pass
    else:
        for u in range(len(potion_use)):
            for potion in potion_use[u]:
                potion_list.append((play_id,timestamp,u+1,"Used",potion))
                
    if len(potion_list) > 0:
        stmt = "INSERT INTO potiondetail values (%s,%s,%s,%s,%s)"
        InsertData(stmt,potion_list)

# Loads events table as defined at the bottom of this script
# Lots of variability in present keys, so try/except was necessary
def Events(play_id, timestamp, event_choices, falling_options):
    event_list = []
    falling_list = []
    for event in event_choices:
        floor = event["floor"]
        event_name = event["event_name"]
        player_choice = event["player_choice"]
        try:
            cards_removed = event["cards_removed"]
        except:
            cards_removed = []
        damage_healed = event["damage_healed"]
        gold_gain = event["gold_gain"]
        damage_taken = event["damage_taken"]
        try:
            relics_obtained = event["relics_obtained"]
        except:
            relics_obtained = []
        max_hp_gain = event["max_hp_gain"]
        max_hp_loss = event["max_hp_loss"]
        try:
            potions_obtained = event["potions_obtained"]
        except:
            potions_obtained = []
        gold_loss = event["gold_loss"]
        try:
            cards_upgraded = event["cards_upgraded"]
        except:
            cards_upgraded = []
        try:
            cards_obtained = event["cards_obtained"]
        except:
            cards_obtained = []
        try:
            relics_lost = event["relics_lost"]
        except:
            relics_lost = []
        if event_name == "Falling":
            for card in falling_options:
                falling_list.append((play_id,timestamp,"N",card))
            falling_list.append((play_id,timestamp,"Y",cards_removed[0]))
            stmt = "INSERT INTO fallinglog values (%s,%s,%s,%s)"
            InsertData(stmt, falling_list)
        event_list.append((play_id, timestamp, floor, event_name, player_choice, str(cards_removed),damage_healed,gold_gain,damage_taken,str(relics_obtained),max_hp_gain,max_hp_loss,str(potions_obtained),gold_loss,str(cards_upgraded),str(cards_obtained),str(relics_lost)))
    event_list = list(dict.fromkeys(event_list))
    stmt = "INSERT INTO events values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    InsertData(stmt,event_list)

# Loads neowdetails table as defined at the bottom of this script
# Opted for one row per bonus presented, indicating if bonus was skipped or picked
# This can be cleaned up so empty lists are not put into table as []
def NeowDetails(rundata):
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    neow_list = []
    try:
        neow_skip = rundata["neow_bonuses_skipped_log"]
    except:
        neow_skip=[]
    try:
        neow_skip_costs = rundata["neow_costs_skipped_log"]
    except:
        neow_skip_costs = []
    neow_pick = rundata["neow_bonus"]
    neow_pick_cost = rundata["neow_cost"]
    try:
        details = rundata["neow_bonus_log"]
    except:
        details = []
    if len(neow_skip) > 0:
        for s in range(len(neow_skip)):
            neow_list.append((play_id, timestamp, neow_skip[s], neow_skip_costs[s], "N","","","","","",0,0,0,0,0))
    if len(details) > 0:
        neow_list.append((play_id, timestamp, neow_pick, neow_pick_cost,"Y",str(details["cardsObtained"]),str(details["cardsUpgraded"]),str(details["cardsRemoved"]), str(details["cardsTransformed"]), str(details["relicsObtained"]), details["maxHpGained"], details["goldGained"], details["damageTaken"], details["goldLost"], details["maxHpLost"]))
    else:
        neow_list.append((play_id, timestamp, neow_pick, neow_pick_cost,"Y","","","","","",0,0,0,0,0))
    stmt = "INSERT INTO neowdetails values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    InsertData(stmt, neow_list)

# Loads shoppurchases and shopskipped tables as definited at the bottom of this script
# Includes cards removed as "Purge" object type
# Since purchases don't include type of purchase (potion, card, relic), an update statement is needed at the very end of the script
def Shops(rundata):
    purchase_list = []
    skip_list = []
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    items_purged = rundata["items_purged"]
    purge_floors = rundata["items_purged_floors"]
    items_purchased = rundata["items_purchased"]
    purchased_floors = rundata["item_purchase_floors"]
    if len(items_purged) > 0:
        for x in range(len(items_purged)):
            purchase_list.append((play_id, timestamp, purge_floors[x], "Remove", items_purged[x]))
    if len(items_purchased) > 0:
        for x in range(len(items_purchased)):
            purchase_list.append((play_id, timestamp, purchased_floors[x], "", items_purchased[x]))
    stmt = "INSERT INTO shoppurchases values (%s,%s,%s,%s,%s)"
    InsertData(stmt,purchase_list)
    try:
        contents = rundata["shop_contents"]
    except:
        contents = []
    if len(contents) > 0:
        for shoplist in contents:
            for potion in shoplist["potions"]:
                skip_list.append((play_id, timestamp, shoplist["floor"], "Potion", potion))
            for relic in shoplist["relics"]:
                skip_list.append((play_id, timestamp, shoplist["floor"], "Relic", relic))
            for card in shoplist["cards"]:
                skip_list.append((play_id, timestamp, shoplist["floor"], "Card", card))
    stmt = "INSERT INTO shopskipped values (%s,%s,%s,%s,%s)"
    InsertData(stmt,skip_list)

# The main function that runs all the above functions
# Some didn't need all the rundata so only specific data is sent to fulfill the data requirements
# Entire run data is passed when multiple different keys are needed
# When specific key is needed to be passed, we use a try in case a run doesn't have it
def LoadRun(rundata):
    play_id = rundata["play_id"]
    timestamp = rundata["timestamp"]
    print(rundata["victory"])
    RunInfo(rundata)
    MasterDeck(play_id, timestamp, rundata["master_deck"])
    FloorInfo(rundata)
    
    try:
        score_breakdown = rundata["score_breakdown"]
    except:
        pass
    else:
        ScoreDetail(play_id, timestamp, score_breakdown)
    
    try:
        card_choices = rundata["card_choices"]
    except:
        pass
    else:
        CardRewards(play_id, timestamp, card_choices)
    
    try:
        relic_stats = rundata["relic_stats"]
    except:
        pass
    else:
        Relics(play_id,timestamp,relic_stats)
    
    RelicsMissed(rundata)
    
    try:
        campfire_choices = rundata["campfire_choices"]
    except:
        pass
    else:
        RestSites(play_id, timestamp, campfire_choices)
        
    try:
        boss_relics = rundata["boss_relics"]
    except:
        pass
    else:
        BossRelics(play_id,timestamp,boss_relics)
    
    try:
        damage_taken = rundata["damage_taken"]
    except:
        pass
    else:
        Combats(play_id, timestamp,damage_taken)
        
    try:
        lesson_learned = rundata["lesson_learned_per_floor"]
    except:
        pass
    else:
        LessonLearned(play_id, timestamp, lesson_learned)
    
    PotionDetails(rundata)
    
    try:
        falling_options = rundata["falling_options_log"]
    except:
        falling_options = []
    try:
        event_choices = rundata["event_choices"]
    except:
        pass
    else:
        Events(play_id, timestamp, event_choices, falling_options)
        
    NeowDetails(rundata)
    
    Shops(rundata)

def main():
    runpath = "//path//to//runs//"
    filenames = listdir(runpath)
    filenames.sort()
    for file in filenames:
        rfile = open(runpath+file,"r")
        LoadRun(json.loads(rfile.read()))
        rfile.close()
    # Below is needed to set object types in shoppurchases table due to run data not specifying object type of purchases
    # The referenced table, s_object, is a static table containing all cards, relics, and potions from the base game
    # Data includes both internal and visible names. s_object can obviously contain data from mods as well
    updstmt = "UPDATE shoppurchases p left join s_object o on substring_index(p.object_name,'+',1) = o.internal_id set p.object_type = o.object_type"
    UpdateData(updstmt)
    
if __name__ == "__main__":
    main()
    
#Below is table DDL used as generated by dBeaver

"""
-- sts.bossrelics definition

CREATE TABLE `bossrelics` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `picked` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `relic` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.cardrewards definition

CREATE TABLE `cardrewards` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `picked` varchar(100) DEFAULT NULL,
  `card_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.combats definition

CREATE TABLE `combats` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `turns` smallint DEFAULT NULL,
  `enemy` varchar(100) DEFAULT NULL,
  `damage` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.events definition

CREATE TABLE `events` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(100) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `event_name` varchar(100) DEFAULT NULL,
  `player_choice` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `cards_removed` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `damage_healed` smallint DEFAULT NULL,
  `gold_gain` smallint DEFAULT NULL,
  `damage_taken` smallint DEFAULT NULL,
  `relics_obtained` varchar(100) DEFAULT NULL,
  `max_hp_gain` smallint DEFAULT NULL,
  `max_hp_loss` smallint DEFAULT NULL,
  `potions_obtained` varchar(100) DEFAULT NULL,
  `gold_loss` smallint DEFAULT NULL,
  `cards_upgraded` varchar(2000) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `cards_obtained` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `relics_lost` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.fallinglog definition

CREATE TABLE `fallinglog` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `removed` varchar(5) DEFAULT NULL,
  `card` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.floorinfo definition

CREATE TABLE `floorinfo` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `node_type` varchar(5) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `node_result` varchar(2) DEFAULT NULL,
  `gold_after` smallint DEFAULT NULL,
  `hp_after` smallint DEFAULT NULL,
  `max_hp_after` smallint DEFAULT NULL,
  `playtime_after` smallint unsigned DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.lessonlearned definition

CREATE TABLE `lessonlearned` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `card_name` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.masterdecks definition

CREATE TABLE `masterdecks` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `card` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.neowdetails definition

CREATE TABLE `neowdetails` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `neow_bonus` varchar(100) DEFAULT NULL,
  `neow_cost` varchar(50) DEFAULT NULL,
  `picked` varchar(5) DEFAULT NULL,
  `cards_obtained` varchar(100) DEFAULT NULL,
  `cards_upgraded` varchar(100) DEFAULT NULL,
  `cards_removed` varchar(100) DEFAULT NULL,
  `cards_transformed` varchar(100) DEFAULT NULL,
  `relics_obtained` varchar(100) DEFAULT NULL,
  `max_hp_gain` smallint DEFAULT NULL,
  `gold_gain` smallint DEFAULT NULL,
  `damage_taken` smallint DEFAULT NULL,
  `gold_lost` smallint DEFAULT NULL,
  `max_hp_loss` smallint DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.potiondetail definition

CREATE TABLE `potiondetail` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `action` varchar(100) DEFAULT NULL,
  `potion` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.relics definition

CREATE TABLE `relics` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `relic` varchar(100) DEFAULT NULL,
  `floor_obtained` smallint DEFAULT NULL,
  `combats_before` smallint DEFAULT NULL,
  `turns_before` smallint DEFAULT NULL,
  `logged_stat` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.relicsmissed definition

CREATE TABLE `relicsmissed` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `relic` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `why_missed` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.restsites definition

CREATE TABLE `restsites` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `action` varchar(15) DEFAULT NULL,
  `detail` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.runinfo definition

CREATE TABLE `runinfo` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `character_chosen` varchar(50) DEFAULT NULL,
  `playtime` smallint unsigned DEFAULT NULL,
  `floor_reached` smallint DEFAULT NULL,
  `local_time` varchar(15) DEFAULT NULL,
  `seed_source_timestamp` varchar(20) DEFAULT NULL,
  `circlet_count` smallint DEFAULT NULL,
  `seed_played` varchar(25) DEFAULT NULL,
  `seed_played_ingame` varchar(20) DEFAULT NULL,
  `is_trial` varchar(10) DEFAULT NULL,
  `is_prod` varchar(10) DEFAULT NULL,
  `is_daily` varchar(10) DEFAULT NULL,
  `chose_seed` varchar(10) DEFAULT NULL,
  `build_version` varchar(25) DEFAULT NULL,
  `victory` varchar(10) DEFAULT NULL,
  `player_experience` varchar(10) DEFAULT NULL,
  `is_beta` varchar(10) DEFAULT NULL,
  `is_endless` varchar(10) DEFAULT NULL,
  `is_ascension_mode` varchar(10) DEFAULT NULL,
  `ascension_level` smallint DEFAULT NULL,
  `gold` smallint DEFAULT NULL,
  `total_combats` smallint DEFAULT NULL,
  `total_turns` smallint DEFAULT NULL,
  `score` smallint DEFAULT NULL,
  `green_key` smallint DEFAULT NULL,
  `killed_by` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.s_object definition

CREATE TABLE `s_object` (
  `object_type` varchar(10) DEFAULT NULL,
  `internal_id` varchar(100) DEFAULT NULL,
  `game_name` varchar(100) DEFAULT NULL,
  `source` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.scoredetail definition

CREATE TABLE `scoredetail` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `score_desc` varchar(100) DEFAULT NULL,
  `score_value` smallint DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.shoppurchases definition

CREATE TABLE `shoppurchases` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `object_type` varchar(15) DEFAULT NULL,
  `object_name` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- sts.shopskipped definition

CREATE TABLE `shopskipped` (
  `play_id` varchar(100) DEFAULT NULL,
  `timestamp` varchar(10) DEFAULT NULL,
  `floor` smallint DEFAULT NULL,
  `object_type` varchar(25) DEFAULT NULL,
  `object_name` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""
