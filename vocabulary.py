#生成单词本
import requests,re,glob,nltk,threading,traceback
# from nltk.stem.wordnet import WordNetLemmatizer 
# from nltk.tokenize import word_tokenize 
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
Max_lematizing  = 4
Max_connentions = 10
from bs4 import BeautifulSoup
from tqdm import tqdm


class vocabulary():
	def __init__(self):
		self.filelist = glob.glob('./data/*.*')
		self.name = glob.glob('./data/*.*')[0].split('\\')[-1].split('.')[0]
		self.key = open('key.txt','r').read()
	def work(self):
		for file in self.filelist:
			raw_text,text = self.get_contents(file)
			self.counts(text)
			words = self.lemmatizing(text)
			
			# filename = './result/' + self.name + '_raw.txt'
			# words = []
			# with open(filename,'r',encoding='utf-8') as f:
				# for line in f:
					# line = line.replace('\n','')
					# words.append(line)
			
			words=self.remove_words(words)
			self.write_word_list(words,raw_text)
	
	
	def get_contents(self,file): #获取内容，输入文件名，返回字符串。
		with open(file,'r',encoding='utf-8') as f:
			raw_text = f.read()
		text = raw_text.lower()
		for ch in '''`~!@#$%^&*()_+-={}|[]\\:"?>”<;'“—‘’.…/,''':
			text = text.replace(ch,' ')
		return raw_text,text
	
	def counts(self,text): #粗糙计数，输入字符串，写入词频文件
		words = text.split()
		counts = {}
		for word in words:
			counts[word] = counts.get(word,0) +1
		items = list(counts.items())
		items.sort(key=lambda x:x[1],reverse=True)
		filename = './result/' + self.name + '_word frequency.txt'
		with open(filename,'w',encoding='utf-8') as f:
			for i in range(len(items)):
				f.write('{0:<10}{1:>5}\n'.format(items[i][0],items[i][1]))		
		
	def lemmatizing(self,text): #词形还原，输入字符串，返回无重复的单词列表，写入raw单词本。
		words = list(set(text.split()))
		lemm_words = []
		threads = []
		global Max_lematizing
		semaphore = threading.Semaphore(Max_lematizing)
		with tqdm(total = len(words),desc='lemmatizing') as fbar:
			for i in range(len(words)):
				semaphore.acquire()
				# self.get_lemmed(words[i],lemm_words,semaphore)
				t = threading.Thread(target=self.get_lemmed,args=(words[i],lemm_words,semaphore))
				threads.append(t)
				t.start()
				if i%1000==0:
					fbar.update(1000)
			for t in threads:
				t.join()
		words = list(set(lemm_words))
		filename = './result/' + self.name + '_raw.txt'
		with open(filename,'w',encoding='utf-8') as f:
			for word in words:
				f.write(word+'\n')
		return words						
	
	def get_lemmed(self,word,lemm_words,semaphore):
		try:
			tag = nltk.pos_tag([word])
			pos = self.get_pos(tag[0][1])
			if pos:
				lemm_word = lemmatizer.lemmatize(word,pos)
				lemm_words.append(lemm_word)
			else:
				lemm_words.append(word)
		except:
			print(word)
		finally:
			semaphore.release()
	
	
	def get_pos(self,treebank_tag):
		if treebank_tag.startswith('J'):
			return nltk.corpus.wordnet.ADJ
		elif treebank_tag.startswith('V'):
			return nltk.corpus.wordnet.VERB
		elif treebank_tag.startswith('N'):
			return nltk.corpus.wordnet.NOUN
		elif treebank_tag.startswith('R'):
			return nltk.corpus.wordnet.ADV
		else:
			return ''
	
	def remove_words(self,words): #去除已经认识的单词，写入refined文件，返回单词列表
		learned_words=[]
		with open('learned_words.txt','r',encoding='utf-8') as f:
			for line in f:
				line = line.replace('\n','')
				learned_words.append(line)
		words = list(set(words) - set(learned_words))
		filename = './result/' + self.name + '_refined.txt'
		with open(filename,'w',encoding='utf-8') as f:
			for word in words:
				f.write(word+'\n')
		return words						
	def download_audio(self,key,url):
		resp = requests.get(url)
		filename = './result/audio/' + key +'.mp3'
		with open(filename,'wb') as f:
			f.write(resp.content)
			
	
	def look_up(self,word): #释义，输入单个单词，返回key,ps,pron,pos,acceptation
		url = 'http://dict-co.iciba.com/api/dictionary.php?w={}&key={}'.format(word,self.key)
		resp = requests.get(url)
		resp.encoding = 'utf-8'
		soup = BeautifulSoup(resp.text,'html.parser')
		try:
			key = soup.key.string
			ps = '[{}]'.format(soup.ps.string)
			self.download_audio(key,soup.pron.string)
			pron = '[sound:{}.mp3]'.format(key) 
			pos_list = soup.select('pos')
			acceptation_list = soup.select('acceptation')
			acceptation = pos_list[0].string + ' ' + acceptation_list[0].string.replace('\n','').replace('\r','')
			for i in range(1,len(pos_list)):
				acceptation = acceptation + '<div>' + pos_list[i].string + ' '  + acceptation_list[i].string.replace('\n','').replace('\r','') + '</div>'
			return (key,ps,pron,acceptation)
		except:
			#traceback.print_exc()
			return None
	def get_sen(self,word,text):
		pattern= '\\..*?{}.*?\\.'.format(word) #问题：大单词包含该小单词
		match =re.search(pattern,text)
		if match:
			return match.group(0)[2:]
		else:
			return ' '
	def write_word_list(self,words,text):
		threads=[]
		global Max_connentions
		semaphore = threading.Semaphore(Max_connentions)
		with tqdm(total = len(words),desc='Looking Up') as fbar:
			for i in range(len(words)):
				semaphore.acquire()
				t=threading.Thread(target=self.write_word,args=(words[i],text,semaphore))
				threads.append(t)
				t.start()
				if i%100==0:
					fbar.update(100)
			for t in threads:
				t.join()
	def write_word(self,word,text,semaphore):
		if self.look_up(word):
			key,ps,pron,acceptation=self.look_up(word)
			sen = self.get_sen(word,text)
			filename = './result/' + self.name + '_vocabulary.txt'
			with open(filename,'a',encoding='utf-8') as f:
				txt = '{}\t{}\t{}\t{}\t{}\n'.format(key,ps,pron,acceptation,sen)
				f.write(txt)
		semaphore.release()
		return 1

if __name__ == '__main__':
	vocabulary().work()