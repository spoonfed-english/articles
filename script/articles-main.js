class ArticlePage extends Page
{
	
	wordHighlighter;
	
	constructor()
	{
		super();
		
		this.onAnswerButtonClick = this.onAnswerButtonClick.bind(this);
		
		this.wordHighlighter = new WordHighlighter(this.$content, this.onTooltipShow);
		
		const $buttons = document.querySelectorAll('section.questions .answer .button');
		for(let i = 0; i < $buttons.length; i++)
		{
			$buttons[i].addEventListener('click', this.onAnswerButtonClick);
		}
	}
	
	onAnswerButtonClick(event)
	{
		const $answer = event.target.closest('.answer');
		if($answer)
		{
			$answer.classList.add('open');
		}
	}
	
}

new ArticlePage();
