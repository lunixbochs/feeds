vcl 4.0;

backend default {
    .host = "127.0.0.1";
    .port = "5005";
}

sub vcl_recv {
    if (req.method == "GET" && (
            req.url ~ "^/static/" ||
            req.url ~ "^/favicon.ico" ||
            req.url ~ "^/$" ||
            req.url ~ "^/feeds/")) {
        return (hash);
    }
    return (pass);
}

sub vcl_backend_response {
    set beresp.ttl = 30s;
}

sub vcl_deliver {
}
