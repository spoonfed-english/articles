class Page
{
	
	static ValidThemes = ['light', 'dark'];
	static TippyThemes = {
		'light': 'light-border',
		'dark': 'dark',
	}
	static ThemeRegex = new RegExp(`\\s*(${Object.values(Page.TippyThemes).join('|')})\\s*`, 'g');
	
	theme = Page.load('theme', Page.ValidThemes[0], Page.ValidThemes);
	
	$content = document.querySelector('section.content');
	$nightModeButton = document.getElementById('night-mode-btn');
	
	constructor()
	{
		this.onNightModeButtonClick = this.onNightModeButtonClick.bind(this);
		this.onTooltipShow = this.onTooltipShow.bind(this);
		
		this.setPageClass();
		
		if(this.$nightModeButton)
		{
			this.$nightModeButton.classList.toggle('active', this.theme === 'dark');
			this.$nightModeButton.addEventListener('click', this.onNightModeButtonClick);
		}
		
		tippy('[data-tippy-content]', {
			touch: true,
			allowHTML: true,
			onShow: this.onTooltipShow,
			theme: 'help-popup',
		});
	}
	
	static store(name, value)
	{
		return localStorage.setItem(name, value);
	}
	
	static load(name, defaultValue, validValues)
	{
		const value = localStorage.getItem(name) || defaultValue;
		
		if(validValues && validValues.length && validValues.indexOf(value) === -1)
			return validValues[0];
		
		return value;
	}
	
	setPageClass()
	{
		for(const theme of Page.ValidThemes)
		{
			document.body.classList.remove(`theme-${theme}`);
		}
		
		document.body.classList.add(`theme-${this.theme}`);
	}
	
	changeTheme(newTheme)
	{
		if(this.theme === newTheme)
			return;
		if(Page.ValidThemes.indexOf(newTheme) === -1)
			return;
		
		if(this.$nightModeButton)
		{
			this.$nightModeButton.classList.toggle('active', newTheme === 'dark');
		}
		
		this.theme = newTheme;
		Page.store('theme', this.theme);
		this.setPageClass();
	}
	
	onNightModeButtonClick()
	{
		this.changeTheme(this.$nightModeButton.classList.contains('active') ? 'light' : 'dark');
	}
	
	onTooltipShow(instance)
	{
		const tippyTheme = Page.TippyThemes[this.theme];
		
		const $tippyDiv = instance.popper.querySelector('.tippy-box');
		const tippyThemeClass = $tippyDiv.dataset.theme.replace(Page.ThemeRegex, '');
		
		instance.setProps({
			theme: `${tippyTheme} ${tippyThemeClass}`,
		});
	}

}

class WordHighlighter
{
	
	static POSRegex = /^([a-z]+)\t(.+)$/gm;
	static POSSub = `<span class="pos">$1</span> <span class="text">$2</span>`;
	
	static ValidWordLists = ['ielts', 'cet6', 'off'];
	
	wordList = Page.load('wordList', WordHighlighter.ValidWordLists[0], WordHighlighter.ValidWordLists);
	$wordListButtons = {};
	
	$content;
	onTooltipShow;
	
	constructor($content, onTooltipShow)
	{
		this.onWordListButtonClick = this.onWordListButtonClick.bind(this);
		this.onWordTooltipShow = this.onWordTooltipShow.bind(this);
		
		this.$content = $content;
		this.onTooltipShow = onTooltipShow;
		
		this.setContentClass();
		
		const $wordListButtons = document.querySelectorAll('.word-lists .item');
		for(const $button of $wordListButtons)
		{
			$button.addEventListener('click', this.onWordListButtonClick);
			$button.classList.remove('active');
			const type = $button.dataset.type;
			this.$wordListButtons[type] = $button;
		}
		
		this.$wordListButtons[this.wordList].classList.add('active');
		
		tippy.delegate($content, {
			target: 'span.word',
			touch: true,
			content: '...',
			trigger: 'click',
			interactive: true,
			allowHTML: true,
			onShow: this.onWordTooltipShow,
			theme: 'definition-popup',
		});
	}
	
	changeWordList(newWordList)
	{
		if(this.wordList === newWordList)
			return;
		if(WordHighlighter.ValidWordLists.indexOf(newWordList) === -1)
			return;
		
		this.$wordListButtons[this.wordList].classList.remove('active');
		this.$wordListButtons[newWordList].classList.add('active');
		
		this.wordList = newWordList;
		Page.store('wordList', this.wordList);
		this.setContentClass();
	}
	
	setContentClass()
	{
		this.$content.className = '';
		this.$content.classList.add('content');
		
		if(this.wordList !== 'off')
		{
			this.$content.classList.add(this.wordList);
		}
	}
	
	onWordListButtonClick(event)
	{
		this.changeWordList(event.target.dataset.type);
	}
	
	onWordTooltipShow(instance)
	{
		if(this.onTooltipShow)
		{
			this.onTooltipShow(instance);
		}
		
		const $word = instance.reference;
		
		if(!$word.classList.contains(this.wordList) && !$word.classList.contains('extra'))
			return false;
		
		const word = $word.innerText;
		const key = $word.dataset.lemma || word;
		let definition = DICT[key];
		
		if(!definition)
			return false;
		
		if(definition[0] === '>')
		{
			definition = DICT[definition.substring(1)];
		}
		
		if(definition[0] !== '<')
		{
			definition = definition.replace(WordHighlighter.POSRegex, WordHighlighter.POSSub);
			
			if(definition[0] !== '<')
			{
				definition = `<span class="text">${definition}</span>`;
			}
		}
		
		instance.setContent(`<div class="definitions">${definition}</div>`);
	}

}
