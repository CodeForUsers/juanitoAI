# core/web_search.py
# Creado y diseñado por David Carreres Gómez.

import logging
from duckduckgo_search import DDGS
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger("juanito.web_search")


class WebSearchManager:
    """Maneja las búsquedas web y el scrapping profundo."""
    
    def __init__(self):
        pass

    def search(self, query: str, max_results: int = 3) -> str:
        """Búsqueda rápida. Devuelve títulos y snippets."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                
            if not results:
                return "No he encontrado nada en la web."
                
            formateado = "🌐 **Resultados de la Búsqueda Ráida:**\n\n"
            for r in results:
                formateado += f"🔹 **{r['title']}**\n{r['body']}\n[Enlace]({r['href']})\n\n"
            return formateado
            
        except Exception as e:
            logger.error(f"Error en web search: {e}")
            return "Se me cayó el internet, compadre. No pude buscar."

    async def _fetch_url_text(self, url: str) -> str:
        """Descarga el HTML y extrae el texto puro usando BeautifulSoup."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=15) as response:
                    if response.status != 200:
                        return ""
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Limpiar scripts y estilos
                    for script in soup(["script", "style"]):
                        script.extract()
                        
                    text = soup.get_text(separator=' ', strip=True)
                    return text[:4000]
        except Exception as e:
            logger.error(f"Error scrapeando {url}: {e}")
            return ""

    async def deep_search(self, query: str, llm_manager) -> str:
        """
        Búsqueda profunda (Fase 5). Busca en DDG, descarga el contenido de las 
        páginas y lo usa como contexto para que el LLM responda.
        """
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=2))
                
            if not results:
                return "No he encontrado nada en la web para investigar."

            contexto_scraper = []
            enlaces_usados = []
            
            for r in results:
                enlaces_usados.append(r['href'])
                texto_web = await self._fetch_url_text(r['href'])
                if texto_web:
                    contexto_scraper.append(f"--- Fila de Fuente: {r['title']} ---\n{texto_web}")

            if not contexto_scraper:
                return "Encontré enlaces pero no pude leer el contenido (cifrado, capchas, etc)."

            # Juntar el contexto y dárselo a Ollama
            texto_unido = "\n\n".join(contexto_scraper)
            from core.config import OLLAMA_MODEL_CHAT
            
            mensajes = [
                {
                    "role": "system",
                    "content": "Eres un asistente de investigación. Tienes la siguiente información estructurada extraída directamente de artículos web. Tu trabajo es leer toda esta información y elaborar una respuesta completa, detallada y en formato legible (usa Markdown, listas, negritas) respondiendo a la pregunta original del usuario. Solo guíate de este contexto.\n\nCONTEXTO EXTRAÍDO:\n" + texto_unido
                },
                {"role": "user", "content": f"PREGUNTA DEL USUARIO: {query}"}
            ]
            
            respuesta_llm = await llm_manager.chat(model=OLLAMA_MODEL_CHAT, messages=mensajes)
            
            # Formatear la respuesta final
            footer = "\n\n📚 **Fuentes consultadas:**\n" + "\n".join([f"- {url}" for url in enlaces_usados])
            return respuesta_llm + footer
            
        except Exception as e:
            logger.error(f"Error en deep search: {e}")
            return "El agente de investigación falló estrepitosamente. Inténtalo más tarde."
