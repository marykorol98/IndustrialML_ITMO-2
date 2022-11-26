# IndustrialML_ITMO-2

In  real-world  industrial  tasks  it  is  often  necessary  to  analyze  and  make  predictions  using  data  of different  modalities.  Modern  models  allow  to  combine  text  and  image  vector  representations effectively,  to  select  the  most  informative  features  and  to  solve  a  wide  range  of  classification  and regression problems.

Here we learn to predict the genre of a film from a pre-approved list of categories based on the title, poster (image), and a synopsis of the film.

The data collected for training and validation: film titles, posters, and short descriptions(synopsis) from imdb.com. For this purpose, IMDb API was used: https://github.com/IMDb-API/IMDbApiLib. 7146 movies data was obtained in 24 categories:
1. Action
2. Adventure
3. Animation
4. Biography
5. Comedy
6. Crime
7. Documentary
8. Drama
9. Family
10. Fantasy
11. Film Noir
12. History
13. Horror
14. Music
15. Musical
16. Mystery
17. Romance
18. Sci-Fi
19. Short Film
20. Sport
21. Superhero
22. Thriller
23. War
24. Western

Several algorithms and model were tested to extract informative features from text and images, among them there are:
- sklearn models with OneVsRest classification
- LSTM
- ResNet
- VGG16

