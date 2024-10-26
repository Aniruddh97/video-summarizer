Docker build
```
docker build -t video-mash .
```


Docker run 
```
docker run --network host -v $(pwd):/app video-mash
```