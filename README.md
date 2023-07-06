# Web-Proxy-Server

This server fetches items from the web on behalf of a web client instead of fetching them directly. Through this page caching and access control is enabled.

What this proxy is able to do:
- Responds to both HTTP and HTTPS requests and display each request in the console.
- Can dynamically block selected URLs from the console, disabling those certain pages from being loaded.
- Caches HTTP requests locally, allowing the saving of bandwidth. The loading times are also displayed in the console for each request, with it being lowered if the page is already cached.
- Can handle multiple connections through the use of threading.
