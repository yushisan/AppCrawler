# -*- coding:utf-8 -*-

# 需要安装pymysql

import pymysql, multiprocessing, re, time, datetime, os

#windows
#root = 'G:/'

#Linux
root = '../Android/'

market_id_dict = {
	'googleplay': '0',
	'googleplayeng': '1',
	'yingyongbao': '2',
	'baidu': '3',
	'360': '4',
	'huawei': '5',
	'xiaomi': '6',
	'wandoujia': '7',
	'hiapk': '8',
	'anzhi': '9',
	'91': '10'
}

def connect_mysql():
	try:
		conn = pymysql.connect(host='localhost', port=3306, user='root', password='pkuoslab', db='Android', charset='utf8')
		return conn
	except:
		print ("数据库连接失败")
		return None

def parse_number(market, line):
	cnword_multi_2 = {
		'十万': 100000,
		'百万': 1000000,
		'千万': 10000000,
		'十亿': 1000000000,
		'百亿': 10000000000,
		'千亿': 100000000000,
		'万亿': 1000000000000
	}
	cnword_multi_1 = {
		'十': 10,
		'百': 100,
		'千': 1000,
		'万': 10000,
		'亿': 100000000
	}
	line = line.replace("+", "").replace(",", "").replace(" ", "").replace("%", "")
	if line == 'NaN': return "0"
	numstr = re.findall("[0-9\.]+", line)
	if len(numstr):
		for cnword in cnword_multi_2.keys():
			if line.endswith(cnword):
				return str(int(float(numstr[-1])*cnword_multi_2[cnword]))
		for cnword in cnword_multi_1.keys():
			if line.endswith(cnword):
				return str(int(float(numstr[-1])*cnword_multi_1[cnword]))
		return str(int(float(numstr[-1])))
	return ""

def parse_rating(market, line):
	full_score = {
		'googleplay': 5,
		'googleplayeng': 5,
		'yingyongbao': 5,
		'baidu': 100,
		'360': 10,
		'huawei': 10,
		'xiaomi': 10,
		'hiapk': 5,
		'anzhi': 10,
		'91': 5
	}
	numstr = re.findall("[0-9\.]+", line)
	if len(numstr):
		return str(float(numstr[0])*10.0/full_score[market])
	return ""

def parse_date(market, line):
	engmonth_num = {
		'Jan': '01',
		'Feb': '02',
		'Mar': '03',
		'Apr': '04',
		'May': '05',
		'Jun': '06',
		'Jul': '07',
		'Aug': '08',
		'Sep': '09',
		'Oct': '10',
		'Nov': '11',
		'Dec': '12'
	}
	updatetimestr = ""
	if market == 'googleplay' or market == 'yingyongbao' or market == 'anzhi':
		matcher = re.findall("[0-9]+年", line)
		if len(matcher):
			year = matcher[0].replace("年", "")
			matcher = re.findall("[0-9]+月", line)
			if len(matcher):
				month = matcher[0].replace("月", "")
				matcher = re.findall("[0-9]+日", line)
				if len(matcher):
					day = matcher[0].replace("日", "")
					updatetimestr = year+"-"+month+"-"+day+" 00:00:00"
	elif market == '360' or market == 'huawei' or market == 'xiaomi' or market == 'hiapk':
		updatetimestr = line+" 00:00:00"
	elif market == '91':
		updatetimestr = line[:-1]+":00"
	elif market == 'googleplayeng' or market == 'wandoujia':
		if line[0:3] in engmonth_num:
			month = engmonth_num[line[0:3]]
			matcher = re.findall("[0-9]+,", line)
			if len(matcher):
				day = matcher[0].replace(",", "")
				matcher = re.findall(", [0-9]+", line)
				if len(matcher):
					year = matcher[0].replace(", ", "")
					updatetimestr = year+"-"+month+"-"+day+" 00:00:00"
	return str(int(time.mktime(time.strptime(updatetimestr, "%Y-%m-%d %H:%M:%S"))))

def parse_info(market, info):
	info_line = info.split("\n")
	key = ""
	result = {}
	for line in info_line:
		line = line.replace("\r", "").replace("\n", "")
		if line.startswith("\t"):
			if key == "Name" or key == "Category" or key == "Tag" or key == "Developer" or key == "Edition":
				result[key] = line[1:].replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"")
			elif key == "Rating":
				result[key] = parse_rating(market, line[1:])
			elif key == "Rating_Num":
				result[key] = parse_number(market, line[1:])
			elif key == "Download":
				result[key] = parse_number(market, line[1:])
			elif key == "Similar_Apps":
				if key in result:
					result[key] += ";"+line[1:]
				else:
					result[key] = line[1:]
			elif key == "Update_Time":
				result[key] = parse_date(market, line[1:])
			elif key.endswith("-Star_Rating_Num"):
				result[key] = parse_number(market, line[1:])
		else:
			key = line
	if "1-Star_Rating_Num" in result and "2-Star_Rating_Num" in result and "3-Star_Rating_Num" in result and "4-Star_Rating_Num" in result and "5-Star_Rating_Num" in result:
		result["Star_Rating_Num"] = result["1-Star_Rating_Num"]+";"+result["2-Star_Rating_Num"]+";"+result["3-Star_Rating_Num"]+";"+result["4-Star_Rating_Num"]+";"+result["5-Star_Rating_Num"]
	return result

def update_apk_metadata(marketid, pkgname, md5str, info_dict, perm_all, desc_all, rlnt_all):
	conn = connect_mysql()
	if (conn == None): return False
	cursor = conn.cursor()
	try:
		if "Update_Time" in info_dict:
			ifexists = cursor.execute("select ID from Market_APK_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and UpTime =(select max(UpTime) from Market_APK_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and UpTime < "+info_dict["Update_Time"]+")")
			if (ifexists == 0):
				last_id = None
			else:
				last_id = str(cursor.fetchall()[0][0])
		else:
			last_id = None
		ifexists = cursor.execute("select ID from Market_APK_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and MD5 = '"+md5str+"'")
		if (ifexists == 0):
			cursor.execute("insert into Market_APK_Metadata (MarketID, Package_Name, MD5) values ("+marketid+", '"+pkgname+"', '"+md5str+"')")
			conn.commit()
			ifexists = cursor.execute("select ID from Market_APK_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and MD5 = '"+md5str+"'")
		update_id = str(cursor.fetchall()[0][0])
		update_str = ""
		if "Edition" in info_dict: update_str += ", Version='"+info_dict['Edition'][:29]+"'"
		if last_id != None: update_str += ", Last_ID="+last_id
		if "Category" in info_dict: update_str += ", Category='"+info_dict['Category'][:39]+"'"
		if "Tag" in info_dict: update_str += ", Tag='"+info_dict['Tag'][:119]+"'"
		if desc_all != None: update_str += ", Description='"+desc_all[:4999]+"'"
		if perm_all != None: update_str += ", PermEx='"+perm_all[:2999]+"'"
		if "Update_Time" in info_dict: update_str += ", UpTime="+info_dict['Update_Time']
		if rlnt_all != None: update_str += ", ReleaseNote='"+rlnt_all[:1499]+"'"
		if len(update_str):
			cursor.execute("update Market_APK_Metadata set"+update_str[1:]+" where id = "+update_id)
			conn.commit()
		cursor.close()
		conn.close()
		return True
	except:
		cursor.close()
		conn.close()
		print (marketid+"：错误！"+pkgname+"/{"+md5str+"} (APK_MetaData Exception)")
		return False

def update_time_metadata(marketid, pkgname, timestr, info_dict):
	conn = connect_mysql()
	if (conn == None): return False
	cursor = conn.cursor()
	try:
		ifexists = cursor.execute("select ID from Market_Time_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and Time = "+timestr)
		if (ifexists == 0):
			cursor.execute("insert into Market_Time_Metadata (MarketID, Package_Name, Time) values ("+marketid+", '"+pkgname+"', "+timestr+")")
			conn.commit()
			ifexists = cursor.execute("select ID from Market_Time_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and Time = "+timestr)
		update_id = str(cursor.fetchall()[0][0])
		update_str = ""
		if "Rating" in info_dict: update_str += ", Avg_rating="+info_dict['Rating']
		if "Download" in info_dict: update_str += ", Downloads="+info_dict['Download']
		if "Rating_Num" in info_dict: update_str += ", Total_rating="+info_dict['Rating_Num']
		if "Similar_Apps" in info_dict: update_str += ", SimilarApps='"+info_dict['Similar_Apps'][:499]+"'"
		if "Star_Rating_Num" in info_dict: update_str += ", Stars='"+info_dict['Star_Rating_Num'][:59]+"'"
		if len(update_str):
			cursor.execute("update Market_Time_Metadata set"+update_str[1:]+" where id = "+update_id)
			conn.commit()
		cursor.close()
		conn.close()
		return True
	except:
		cursor.close()
		conn.close()
		print (marketid+"：错误！"+pkgname+"/["+timestr+"] (Time_MetaData Exception)")
		return False

def update_app_metadata(marketid, pkgname, urlsuffix, timestr, md5str, info_dict):
	conn = connect_mysql()
	if (conn == None): return False
	cursor = conn.cursor()
	try:
		ifexists = cursor.execute("select ID from Market_APP_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"'")
		if (ifexists == 0):
			cursor.execute("insert into Market_APP_Metadata (MarketID, Package_Name) values ("+marketid+", '"+pkgname+"')")
			conn.commit()
			ifexists = cursor.execute("select ID from Market_APP_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"'")
		update_id = str(cursor.fetchall()[0][0])
		update_str = ""
		ifexists = cursor.execute("select ID from Market_APK_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"' and UpTime =(select max(UpTime) from Market_APK_Metadata where MarketID = "+marketid+" and Package_Name = '"+pkgname+"')")
		if (ifexists != 0): update_str += ", Market_APK_ID="+str(cursor.fetchall()[0][0])
		update_str += ", Url_Suffix='"+urlsuffix[:319]+"'"
		if "Name" in info_dict: update_str += ", App_Name='"+info_dict['Name'][:99]+"'"
		if "Developer" in info_dict: update_str += ", Developer='"+info_dict['Developer'][:59]+"'"
		if "Category" in info_dict: update_str += ", Category='"+info_dict['Category'][:39]+"'"
		if "Tag" in info_dict: update_str += ", Tag='"+info_dict['Tag'][:119]+"'"
		if "Update_Time" in info_dict:
			ifexists = cursor.execute("select UpTime from Market_APP_Metadata where ID="+update_id)
			exist_updatetime = cursor.fetchall()[0][0]
			if exist_updatetime == None or int(info_dict["Update_Time"]) > exist_updatetime: update_str += ", UpTime="+info_dict['Update_Time']
		ifexists = cursor.execute("select Visittime from Market_APP_Metadata where ID="+update_id)
		exist_visittime = cursor.fetchall()[0][0]
		if exist_visittime == None or int(timestr) > exist_visittime: update_str += ", Visittime="+timestr
		ifexists = cursor.execute("select Deltime from Market_APP_Metadata where ID="+update_id)
		exist_deltime = cursor.fetchall()[0][0]
		if exist_deltime != None and int(timestr) > exist_deltime: update_str += ", Deltime=null"
		cursor.execute("update Market_APP_Metadata set"+update_str[1:]+" where ID="+update_id)
		conn.commit()
		cursor.close()
		conn.close()
		return True
	except:
		cursor.close()
		conn.close()
		print (marketid+"：错误！"+pkgname+"/["+timestr+"] (APP_MetaData Exception)")
		return False

def set_invalid_app_metadata(marketid, urlsuffix, timestr):
	conn = connect_mysql()
	if (conn == None): return False
	cursor = conn.cursor()
	try:
		ifexists = cursor.execute("select ID from Market_APP_Metadata where MarketID = "+marketid+" and Url_Suffix = '"+urlsuffix+"'")
		if (ifexists == 0):
			cursor.close()
			conn.close()
			return False
		update_id = str(cursor.fetchall()[0][0])
		ifexists = cursor.execute("select Visittime from Market_APP_Metadata where ID="+update_id)
		exist_visittime = cursor.fetchall()[0][0]
		if (int(timestr) > exist_visittime):
			ifexists = cursor.execute("select Deltime from Market_APP_Metadata where ID="+update_id)
			exist_deltime = cursor.fetchall()[0][0]
			if (exist_deltime == None):
				cursor.execute("update Market_APP_Metadata set Deltime="+timestr+" where ID="+update_id)
				conn.commit()
				ret = True
			else:
				ret = False
		else:
			ret = False
		cursor.close()
		conn.close()
		return ret
	except:
		cursor.close()
		conn.close()
		print (marketid+"：错误！"+urlsuffix+":["+timestr+"] (APP_MetaData_Invalid Exception)")
		return False

def store(param):
	market = param
	market_id = market_id_dict[market]
	iseng = ""
	if market == 'googleplayeng':
		iseng = "(eng)"
		market = "googleplay"
	while True:
		fin = open(root+'__log__/'+market+'.log', "r")
		success_num = 0
		for line in fin:
			if os.path.isfile('db_exit'):
				fin.close()
				print (market+"：结束")
				return
			line = line.replace("\r", "").replace("\n", "")
			splitspace = line.split(" ")
		#	try:
			if len(splitspace) == 5 and splitspace[1] == 'success':
					timestr = splitspace[0]
					urlsuffix = splitspace[2]
					pkgname = splitspace[3]
					md5str = splitspace[4]
					if os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/end") and os.path.isfile(root+market+"/"+pkgname+"/{"+md5str+"}/end"):
						if (not (os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/db"+iseng))) or not ((os.path.isfile(root+market+"/"+pkgname+"/{"+md5str+"}/db"+iseng))):
							# read information
							if not os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/Information"+iseng+".txt"):
								print (market+iseng+"：错误！"+pkgname+"/["+timestr+"] (Information File Not Found)")
								continue
							fin_info = open(root+market+"/"+pkgname+"/["+timestr+"]/Information"+iseng+".txt", "r")
							info_all = fin_info.read()
							fin_info.close()
							try:
								if len(iseng): info_dict = parse_info("googleplayeng", info_all) 
								else: info_dict = parse_info(market, info_all)
							except:
								print (market+iseng+"：错误！"+pkgname+"/["+timestr+"] (Read Info Exception)")
								continue
							check_key_tuple = ("Download", "Rating", "Rating_Num", "Update_Time")
							fail = False
							for check_key in check_key_tuple:
								if check_key in info_dict and not len(info_dict[check_key]):
									print (market+iseng+"：错误！"+pkgname+"/["+timestr+"] ("+check_key+")")
									fail = True
									break
							if fail:
								continue
							if "Star_Rating_Num" in info_dict and len(re.findall('[0-9]+', info_dict["Star_Rating_Num"])) != 5:
								print (market+iseng+"：错误！"+pkgname+"/["+timestr+"] (Star_Rating_Num)")
								continue
							if not (os.path.isfile(root+market+"/"+pkgname+"/{"+md5str+"}/db"+iseng)):
								if os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/Permission"+iseng+".txt"):
									fin_perm = open(root+market+"/"+pkgname+"/["+timestr+"]/Permission"+iseng+".txt", "r")
									perm_all = fin_perm.read().replace("\\", "\\\\").replace("\r", "").replace("\n", "\\n").replace("\t", "\\t").replace("'", "\\'").replace("\"", "\\\"")
									fin_perm.close()
								else:
									perm_all = None
								if os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/Description"+iseng+".txt"):
									fin_desc = open(root+market+"/"+pkgname+"/["+timestr+"]/Description"+iseng+".txt", "r")
									desc_all = fin_desc.read().replace("\\", "\\\\").replace("\r", "").replace("\n", "\\n").replace("\t", "\\t").replace("'", "\\'").replace("\"", "\\\"")
									fin_desc.close()
								else:
									desc_all = None
								if os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/Release_Note"+iseng+".txt"):
									fin_rlnt = open(root+market+"/"+pkgname+"/["+timestr+"]/Release_Note"+iseng+".txt", "r")
									rlnt_all = fin_rlnt.read().replace("\\", "\\\\").replace("\r", "").replace("\n", "\\n").replace("\t", "\\t").replace("'", "\\'").replace("\"", "\\\"")
									fin_rlnt.close()
								else:
									rlnt_all = None
								if not update_apk_metadata(market_id, pkgname, md5str, info_dict, perm_all, desc_all, rlnt_all): continue
								success_num += 1
								if (success_num % 50 == 0): print (market+iseng+"：成功！"+pkgname+"/{"+md5str+"}")
								#open(root+market+"/"+pkgname+"/{"+md5str+"}/db"+iseng, "w").close()						
							if not (os.path.isfile(root+market+"/"+pkgname+"/["+timestr+"]/db"+iseng)):
								if not update_time_metadata(market_id, pkgname, timestr, info_dict): continue
								if not update_app_metadata(market_id, pkgname, urlsuffix, timestr, md5str, info_dict): continue
								success_num += 1
								if (success_num % 50 == 0): print (market+iseng+"：成功！"+pkgname+"/["+timestr+"]")
								#open(root+market+"/"+pkgname+"/["+timestr+"]/db"+iseng, "w").close()
			elif len(splitspace) == 3 and splitspace[1] == 'invalid':
					timestr = splitspace[0]
					urlsuffix = splitspace[2]
					if not set_invalid_app_metadata(market_id, urlsuffix, timestr): continue
					print (market+iseng+"：无效！"+urlsuffix)
		#	except:
		#		print (market+iseng+"：Unknown Error - "+line)
		fin.close()
		return

if False:
	market = 'googleplayeng'
	fin_info = open("/home/tzeho/Android/googleplay/univers.jaigoga.haneymoon/[1487152503]/Information(eng).txt", "r")
	info_all = fin_info.read()
	fin_info.close()
	info_dict = parse_info(market, info_all)
	for key, value in info_dict.items():
		print (key+" : "+value)
	if "Update_Time" in info_dict:
		print (datetime.datetime.utcfromtimestamp(int(info_dict["Update_Time"])).strftime("%Y-%m-%d %H:%M:%S"))
	exit()

if __name__ == '__main__':
	if (not os.path.exists(root) and len(root) > 0) or not os.path.exists(root+"__log__") or not os.path.isfile("database.txt"): exit()
	if os.path.isfile('db_exit'): os.remove('db_exit')
	fin_settings = open("database.txt", "r")
	market_set = set()
	param_list = []
	for line in fin_settings:
		line = line.replace("\r", "").replace("\n", "")
		if line.startswith('#') or len(line) <= 1: continue
		market = line
		if market in market_set: exit()
		if market in market_id_dict:
			market_set.add(market)
			param_list.append(market)
	fin_settings.close()
	processes = []
	for param in param_list:
		if param == param_list[0]: continue
		processes.append(multiprocessing.Process(target = store, args = (param,)))
	for p in processes:
		p.start()
	store(param_list[0])
	for p in processes:
		p.join()
	print ("正常退出")