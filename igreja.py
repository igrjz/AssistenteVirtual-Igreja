import speech_recognition as sr
import pyttsx3
import os
import psutil
import tkinter as tk
from tkinter import ttk, scrolledtext
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading
import time
import queue
import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Tuple
from database import inicializar_db, adicionar_informacao, registrar_pesquisa, buscar_informacao, listar_topicos




class SystemMonitor:
    """Handles system monitoring and visualization"""
    def __init__(self, parent: tk.Toplevel):
        self.parent = parent
        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.ax_ram = self.fig.add_subplot(211)
        self.ax_cpu = self.fig.add_subplot(212)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.ram_data: List[float] = []
        self.cpu_data: List[float] = []
        self.running = True

    def update(self) -> None:
        """Update monitoring graphs"""
        while self.running and self.parent.winfo_exists():
            ram = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent()
            
            # Update data buffers
            self.ram_data.append(ram)
            self.cpu_data.append(cpu)
            if len(self.ram_data) > 20:
                self.ram_data.pop(0)
                self.cpu_data.pop(0)
            
            # Update plots
            self._update_plot(self.ax_ram, self.ram_data, 'r-', f'Uso de RAM: {ram}%')
            self._update_plot(self.ax_cpu, self.cpu_data, 'b-', f'Uso de CPU: {cpu}%')
            
            self.fig.tight_layout()
            self.canvas.draw()
            time.sleep(1)

    def _update_plot(self, ax, data, style, title) -> None:
        """Helper method to update individual plots"""
        ax.clear()
        ax.plot(data, style)
        ax.set_title(title)
        ax.set_ylim(0, 100)

    def stop(self) -> None:
        """Stop monitoring thread"""
        self.running = False

class JarvisGUI(tk.Tk):
    """Main application GUI for Jarvis assistant"""
    def __init__(self):
        super().__init__()
        self.title("Assistente Jarvis")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self._init_ui()
        self._init_systems()
        self.monitor: Optional[SystemMonitor] = None

    def _init_ui(self) -> None:
        """Initialize user interface components"""
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('TButton', font=('Arial', 10))
        
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log de Interações")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.txt_logs = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.txt_logs.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(ctrl_frame, text="Ouvir Comando", 
                  command=self._start_listening).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Base de Conhecimento",
                  command=self._open_knowledge_base).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Sair", 
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _init_systems(self) -> None:
        """Initialize backend systems"""
        self.voice_engine = pyttsx3.init()
        self.voice_engine.setProperty('rate', 170)
        self.speak_lock = threading.Lock()
        self.command_queue = queue.Queue()

        self.current_search_results = []
        self.selected_result = None
        self.search_cache = {}  # Cache for search results
        inicializar_db()
        self.log("Sistema inicializado. Pronto para ajudar.")



    def log(self, message: str) -> None:
        """Add message to log display"""
        self.txt_logs.config(state='normal')
        self.txt_logs.insert(tk.END, f"{message}\n")
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state='disabled')

    def speak(self, text: str) -> None:
        """Convert text to speech"""
        self.log(f"Jarvis: {text}")
        with self.speak_lock:
            self.voice_engine.say(text)
            self.voice_engine.runAndWait()


    def listen(self) -> Optional[str]:
        """Listen for voice command"""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.log("Ouvindo...")
            try:
                audio = recognizer.listen(source, timeout=5)
                command = recognizer.recognize_google(audio, language='pt-BR')
                self.log(f"Você disse: {command}")
                return command.lower()
            except sr.UnknownValueError:
                self.speak("Desculpe, não entendi.")
            except sr.RequestError:
                self.speak("Erro ao conectar com o serviço de voz.")
            return None

    def execute_command(self, command: str) -> None:
        """Execute the given command"""
        if not command:
            return

        command_handlers = {
            # Notepad variations
            'abrir bloco de notas': self._open_notepad,
            'abre bloco de notas': self._open_notepad,
            'abrir o bloco de notas': self._open_notepad,
            'abre o bloco de notas': self._open_notepad,
            'bloco de notas': self._open_notepad,
            
            # Memory variations
            'limpar memória': self._clear_memory,
            'limpa memória': self._clear_memory,
            'limpar a memória': self._clear_memory,
            
            # System status
            'status': self._show_system_status,
            'status do sistema': self._show_system_status,
            
            # Chrome variations
            'abrir chrome': self._open_chrome,
            'abrir o chrome': self._open_chrome,
            'abre chrome': self._open_chrome,
            
            # Calculator variations
            'abrir calculadora': self._open_calculator,
            'abre calculadora': self._open_calculator,
            
            # Shutdown variations
            'desligar': self._shutdown,
            'desliga': self._shutdown,
            'desligar computador': self._shutdown,
            
            # Restart variations
            'reiniciar': self._restart,
            'reinicia': self._restart,
            'reiniciar computador': self._restart,
            
            # Exit variations
            'sair': self.destroy,
            'fechar': self.destroy,
            'encerrar': self.destroy,
            
            # Search variations
            'pesquisar': self._search_web,
            'buscar': self._search_web,
            'pesquisar sobre': self._search_web,
            'buscar na internet': self._search_web,
            
            # Knowledge variations
            'salvar informação': self._save_current_result,
            'salvar esta informação': self._save_current_result,
            'o que você sabe sobre': self._query_knowledge

        }


        # Normalize command by removing extra spaces and common filler words
        normalized = ' '.join([word for word in command.split() 
                             if word not in ['o', 'a', 'os', 'as', 'de', 'do', 'da']])
        
        for cmd, handler in command_handlers.items():
            if cmd in normalized:
                handler()
                return


        self.speak("Comando não reconhecido.")

    # Command handlers
    def _open_notepad(self) -> None:
        os.system("notepad.exe")
        self.speak("Abrindo bloco de notas.")

    def _clear_memory(self) -> None:
        os.system("cls && echo off | clip")
        self.speak("Memória limpa.")

    def _show_system_status(self) -> None:
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent()
        self.speak(f"Uso de memória: {ram}%. Uso de CPU: {cpu}%")
        
        monitor_window = tk.Toplevel(self)
        monitor_window.title("Monitor de Sistema")
        
        self.monitor = SystemMonitor(monitor_window)
        monitor_thread = threading.Thread(
            target=self.monitor.update,
            daemon=True
        )
        monitor_thread.start()

    def _open_chrome(self) -> None:
        os.system("start chrome")
        self.speak("Abrindo o navegador Chrome.")

    def _open_calculator(self) -> None:
        os.system("calc")
        self.speak("Abrindo a calculadora.")

    def _shutdown(self) -> None:
        self.speak("Desligando o computador em 10 segundos.")
        os.system("shutdown /s /t 10")

    def _restart(self) -> None:
        self.speak("Reiniciando o computador em 10 segundos.")
        os.system("shutdown /r /t 10")

    def _start_listening(self) -> None:
        """Start listening for commands in a separate thread"""
        def listen_thread():
            command = self.listen()
            if command:
                self.execute_command(command)

        threading.Thread(target=listen_thread, daemon=True).start()

    def _search_web(self, query: str = None) -> None:
        """Search the web for information"""
        if not query:
            self.speak("O que você gostaria que eu pesquisasse?")
            query = self.listen()
            if not query:
                return

        # Check cache first
        if query in self.search_cache:
            self.current_search_results = self.search_cache[query]
            self._display_search_results(self.current_search_results)
            self.speak(f"Mostrando resultados em cache para {query}")
            return

        try:
            # Check internet connection first
            try:
                requests.get('https://www.google.com', timeout=5)
            except requests.ConnectionError:
                self.speak("Sem conexão com a internet. Verifique sua rede.")
                return
                
            # URL encode query and handle special characters
            encoded_query = requests.utils.quote(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept-Language': 'pt-BR,pt;q=0.9'
            }
            
            self.log(f"Pesquisando: {query}")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            seen_links = set()  # For deduplication
            
            # More robust result parsing
            for result in soup.select('.tF2Cxc'):
                try:
                    title = result.select_one('h3')
                    link = result.a['href']
                    
                    # Skip duplicates
                    if link in seen_links:
                        continue
                    seen_links.add(link)
                    
                    snippet = result.select_one('.IsZvec, .VwiC3b')
                    if title and link:
                        results.append({
                            'title': title.text.strip(),
                            'link': link,
                            'snippet': snippet.text.strip()[:250] + '...' if snippet else ''
                        })
                        if len(results) >= 5:  # Show more results
                            break
                except Exception as e:
                    self.log(f"Erro ao processar resultado: {str(e)}")
                    continue
            
            # Cache results
            if results:
                self.search_cache[query] = results

            
            if results:
                self.current_search_results = results
                registrar_pesquisa(query, len(results))
                self._display_search_results(results)
                self.log(f"Encontrados {len(results)} resultados para '{query}'")
            else:
                msg = f"Não encontrei resultados para '{query}'. Tente reformular sua pesquisa."
                self.speak(msg)
                self.log(msg)
                
        except requests.exceptions.RequestException as e:
            self.log(f"Erro na pesquisa: {str(e)}")
            self.speak("Ocorreu um erro de rede ao pesquisar. Verifique sua conexão.")
        except Exception as e:
            self.log(f"Erro inesperado na pesquisa: {str(e)}")
            self.speak("Ocorreu um erro inesperado ao pesquisar.")


    def _display_search_results(self, results: List[dict]) -> None:
        """Display search results in a new window"""
        result_window = tk.Toplevel(self)
        result_window.title("Resultados da Pesquisa")
        result_window.geometry("800x600")
        
        # Create scrollable container
        container = ttk.Frame(result_window)
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        container.pack(fill="both", expand=True)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def open_link(url):
            import webbrowser
            webbrowser.open(url)
            
        for idx, result in enumerate(results, 1):
            frame = ttk.LabelFrame(scrollable_frame, text=f"Resultado {idx}")
            frame.pack(fill="x", padx=10, pady=5, ipadx=5, ipady=5)
            
            # Title with clickable link
            title_frame = ttk.Frame(frame)
            title_frame.pack(fill="x", pady=(0,5))
            
            ttk.Label(title_frame, text=result['title'], 
                     font=('Arial', 10, 'bold')).pack(side="left")
            
            link_btn = ttk.Button(title_frame, text="Abrir Link",
                                command=lambda url=result['link']: open_link(url))
            link_btn.pack(side="right", padx=5)
            
            # Snippet text
            ttk.Label(frame, text=result['snippet'], 
                     wraplength=700).pack(anchor='w')
            
            # Select button
            def select_result(result=result):
                self.selected_result = result
                self.speak(f"Selecionado: {result['title']}")
                
            ttk.Button(frame, text="Selecionar para Salvar", 
                      command=select_result).pack(pady=5)


    def _save_current_result(self) -> None:
        """Save the currently selected search result"""
        if not self.selected_result:
            self.speak("Nenhum resultado selecionado para salvar.")
            return
            
        self.speak("Qual tópico devo associar a esta informação?")
        topic = self.listen()
        if topic:
            adicionar_informacao(
                topic,
                f"{self.selected_result['title']}\n{self.selected_result['snippet']}",
                self.selected_result['link']
            )
            self.speak("Informação salva com sucesso na base de conhecimento.")

    def _query_knowledge(self, query: str = None) -> None:
        """Query local knowledge base"""
        if not query:
            self.speak("Sobre o que você gostaria de saber?")
            query = self.listen()
            if not query:
                return
                
        results = buscar_informacao(query)
        if results:
            for topic, info in results:
                self.speak(f"Encontrei sobre {topic}: {info[:100]}...")
        else:
            self.speak("Não encontrei informações sobre este tópico.")

    def _open_knowledge_base(self) -> None:
        """Open knowledge base interface"""
        kb_window = tk.Toplevel(self)
        kb_window.title("Base de Conhecimento")
        kb_window.geometry("800x600")

        # Main container
        main_frame = ttk.Frame(kb_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Topics list (left)
        topics_frame = ttk.Frame(main_frame)
        topics_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        ttk.Label(topics_frame, text="Tópicos").pack()
        self.topics_tree = ttk.Treeview(topics_frame, height=25)
        self.topics_tree.pack(fill=tk.Y)
        self.topics_tree.bind('<<TreeviewSelect>>', self._on_topic_select)

        # Information display (right)
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(info_frame, text="Informação").pack()
        self.info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Buttons (bottom)
        btn_frame = ttk.Frame(kb_window)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Atualizar", 
                 command=self._refresh_topics).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Fechar",
                 command=kb_window.destroy).pack(side=tk.RIGHT, padx=5)

        self._refresh_topics()
        self.speak("Base de conhecimento aberta.")

    def _refresh_topics(self) -> None:
        """Refresh the topics list"""
        self.topics_tree.delete(*self.topics_tree.get_children())
        for topic in listar_topicos():
            self.topics_tree.insert('', 'end', text=topic, values=(topic,))

    def _on_topic_select(self, event) -> None:
        """Handle topic selection"""
        selected = self.topics_tree.focus()
        if selected:
            topic = self.topics_tree.item(selected)['text']
            info = buscar_informacao(topic)
            self.info_text.delete(1.0, tk.END)
            for topic, content in info:
                self.info_text.insert(tk.END, f"{topic}:\n{content}\n\n")



    def on_close(self) -> None:
        """Clean up resources before closing"""
        if self.monitor:
            self.monitor.stop()
        self.destroy()

if __name__ == "__main__":
    app = JarvisGUI()
    app.mainloop()
