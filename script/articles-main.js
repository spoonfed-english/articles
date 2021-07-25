class ArticlePage extends Page
{
	
	wordHighlighter;
	
	constructor()
	{
		super();
		
		this.wordHighlighter = new WordHighlighter(this.$content, this.onTooltipShow);
	}
	
}

new ArticlePage();
